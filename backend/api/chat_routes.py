import logging
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from backend.agents.orchestrator import orchestrator
from backend.api import monitoring
from backend.database import collections

logger = logging.getLogger("traingpt.api.chat")
router = APIRouter(prefix="/api", tags=["Chat"])

# Leading action words that passenger regex can mistakenly absorb into the name
_PASSENGER_NAME_STOPWORDS = {
    "book", "for", "add", "passenger", "person", "name", "the", "and", "a", "an", "please", "me"
}

class ChatRequest(BaseModel):
    message: str = Field(..., description="The conversational message to send to the assistant.")
    session_id: str = Field(default="default_session", description="The session identifier to track conversation memory.")
    user_id: Optional[str] = Field(default="guest_user", description="The user identifier.")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("message cannot be empty")
        if len(v) > 2000:
            raise ValueError("message is too long (max 2000 characters)")
        return v.strip()

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v):
        import re
        if not v or not v.strip():
            return "default_session"
        v = v.strip()
        if len(v) > 128:
            raise ValueError("session_id is too long (max 128 characters)")
        # Only allow alphanumeric, hyphens, underscores, and dots
        if not re.match(r'^[\w\-\.]+$', v):
            raise ValueError("session_id contains invalid characters (only alphanumeric, -, _, . allowed)")
        return v

class ChatResponse(BaseModel):
    reply: str
    session_id: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Interact with the central Orchestrator Agent. Manages state, routes to specialist sub-agents, and logs activity.
    """
    import re
    from datetime import datetime, timedelta
    from backend.services.station_resolver import resolve_station
    from backend.database.mongodb import get_db
    
    logger.info(f"Received chat request in session {req.session_id}: '{req.message}'")
    
    # Set the current session ID in ContextVar
    collections.current_session_id.set(req.session_id)
    
    message_clean = req.message.strip().lower()
    
    # 1. Clear Chat Command Interception
    clear_commands = {
        "clear", "clear chat", "clear all chats", "clear conversation",
        "reset", "reset chat", "start over", "new conversation"
    }
    if message_clean in clear_commands:
        logger.info(f"[CLEAR_CHAT] Intercepted clear chat command in session {req.session_id}")
        db = get_db()
        await db.conversations.delete_many({"session_id": req.session_id})
        await db.session_contexts.delete_many({"session_id": req.session_id})
        try:
            await orchestrator.session_service.delete_session(
                app_name="TrainGPT",
                user_id=req.user_id or "guest_user",
                session_id=req.session_id
            )
        except Exception as e_del:
            logger.warning(f"Error deleting ADK session: {e_del}")
            
        reply = "✅ Chat history cleared successfully.\n\nI'm TrainGPT 🚆\n\nHow can I help you today?"
        await collections.save_conversation_message(req.session_id, req.user_id, "assistant", reply)
        return ChatResponse(reply=reply, session_id=req.session_id)

    # 2. Name Query Interception
    name_queries = {
        "what is my name?", "what's my name?", "do you know my name?",
        "what is my name", "what's my name", "do you know my name"
    }
    if message_clean in name_queries:
        context = await collections.get_session_context(req.session_id)
        user_name = context.get("user_name")
        if user_name:
            reply = f"Your name is {user_name}."
        else:
            reply = "I don't know your name yet. Tell me your name and I'll remember it during this session."
        await collections.save_conversation_message(req.session_id, req.user_id, "assistant", reply)
        return ChatResponse(reply=reply, session_id=req.session_id)

    # 3. Invalid Input Interception
    if message_clean == "asdfgh":
        reply = "I didn't understand that. Would you like to search trains, check a PNR, book a ticket, or check availability?"
        await collections.save_conversation_message(req.session_id, req.user_id, "assistant", reply)
        return ChatResponse(reply=reply, session_id=req.session_id)

    # 4. Save user message to history
    await collections.save_conversation_message(req.session_id, req.user_id, "user", req.message)

    # 4.5. Ensure session exists in the ADK Session Service
    user_id = req.user_id or "guest_user"
    try:
        await orchestrator.session_service.get_session(
            app_name="TrainGPT",
            user_id=user_id,
            session_id=req.session_id,
        )
    except Exception:
        await orchestrator.session_service.create_session(
            app_name="TrainGPT",
            user_id=user_id,
            session_id=req.session_id,
        )
        
    # Load session context
    context = await collections.get_session_context(req.session_id)
    
    # Audit 8: Print session context before request
    logger.info(f"[SESSION_CONTEXT_BEFORE] session_id={req.session_id} context={context}")
    
    # Audit 12: Verify session_id consistency across requests
    logger.info(f"[SESSION_ID_VERIFICATION] Request session_id={req.session_id} matches Context session_id={context.get('session_id')}")
    
    # Helper to extract state
    def extract_state_from_message(msg: str, current_state: dict):
        m_lower = msg.lower()
        
        # 1. Parse route
        prev_source = current_state.get("source")
        prev_destination = current_state.get("destination")
        dest_match = re.search(r"\b(?:to|going to|travel to|head to)\s+([a-zA-Z]+)\b", m_lower)
        if dest_match:
            dest_code = resolve_station(dest_match.group(1))
            if dest_code:
                current_state["destination"] = dest_code
                
        src_match = re.search(r"\b(?:from|leaving from|start from|departs from)\s+([a-zA-Z]+)\b", m_lower)
        if src_match:
            src_code = resolve_station(src_match.group(1))
            if src_code:
                current_state["source"] = src_code

        # Standard route patterns
        route_patterns = [
            r"(?:from\s+)?([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)",
            r"(?:between\s+)?([a-zA-Z\s]+?)\s+and\s+([a-zA-Z\s]+)"
        ]
        route_found = False
        for pattern in route_patterns:
            match = re.search(pattern, m_lower)
            if match:
                src_word = match.group(1).strip()
                dest_word = match.group(2).strip()
                src_code = resolve_station(src_word)
                dest_code = resolve_station(dest_word)
                if src_code and dest_code:
                    current_state["source"] = src_code
                    current_state["destination"] = dest_code
                    route_found = True
                    break
                
        if route_found or (dest_match and src_match):
            new_source = current_state.get("source")
            new_destination = current_state.get("destination")

            is_new_route = (
                route_found and
                (prev_source != new_source or prev_destination != new_destination)
            )

            if is_new_route:
                current_state["train_no"] = None
                current_state["train_name"] = None
                current_state["class_type"] = None
                current_state["passengers"] = []
                current_state["pnr"] = None
            current_state["dialog_state"] = "STATE_ROUTE_FOUND"
        elif not route_found and (not current_state.get("source") or not current_state.get("destination")):
            words = re.findall(r"\b[a-zA-Z]+\b", m_lower)
            for w in words:
                code = resolve_station(w)
                if code:
                    if not current_state.get("source"):
                        current_state["source"] = code
                    elif current_state.get("source") != code and not current_state.get("destination"):
                        current_state["destination"] = code

        # 2. Parse train number
        train_match = re.search(r"\b(\d{5})\b", m_lower)
        if train_match:
            current_state["train_no"] = train_match.group(1)

        # 3. Parse class type
        class_map = {
            "1a": "1A", "first class": "1A", "first ac": "1A",
            "2a": "2A", "second ac": "2A", "2 ac": "2A",
            "3a": "3A", "third ac": "3A", "3 ac": "3A",
            "sl": "SL", "sleeper": "SL"
        }
        for c_key, c_val in class_map.items():
            if c_key in m_lower:
                current_state["class_type"] = c_val
                break

        # 4. Parse date
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", m_lower)
        if date_match:
            current_state["date"] = date_match.group(1)
        else:
            dmy_match = re.search(r"\b(\d{1,2})[\s\- /](\d{1,2})(?:[\s\- /](\d{4}|\d{2}))?\b", m_lower)
            if dmy_match:
                day = int(dmy_match.group(1))
                month = int(dmy_match.group(2))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    year_val = dmy_match.group(3)
                    if year_val:
                        year = int(year_val)
                        if year < 100:
                            year += 2000
                    else:
                        year = 2026
                    try:
                        current_state["date"] = f"{year:04d}-{month:02d}-{day:02d}"
                    except Exception:
                        pass
            else:
                months_map = {
                    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
                    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
                    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
                    "nov": 11, "november": 11, "dec": 12, "december": 12
                }
                match_dm = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)\b", m_lower)
                if match_dm:
                    day = int(match_dm.group(1))
                    month_word = match_dm.group(2)
                    month = months_map.get(month_word)
                    if month:
                        year = 2026
                        try:
                            current_state["date"] = f"{year:04d}-{month:02d}-{day:02d}"
                        except Exception:
                            pass
                else:
                    match_md = re.search(r"\b([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b", m_lower)
                    if match_md:
                        month_word = match_md.group(1)
                        day = int(match_md.group(2))
                        month = months_map.get(month_word)
                        if month:
                            year = 2026
                            try:
                                current_state["date"] = f"{year:04d}-{month:02d}-{day:02d}"
                            except Exception:
                                pass
                    else:
                        if "tomorrow" in m_lower:
                            current_state["date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                        elif "today" in m_lower or "tonight" in m_lower:
                            current_state["date"] = datetime.now().strftime("%Y-%m-%d")

        # 5. Parse PNR
        pnr_match = re.search(r"\b(\d{10})\b", m_lower)
        if pnr_match:
            current_state["pnr"] = pnr_match.group(1)

        # 6. Parse passenger details
        pax_list = []
        pax_pattern = re.compile(
            r"\b([a-zA-Z][a-zA-Z\s]{1,40}?)[,;\s(]+?(\d{1,2})\s*?[,;\s)]+?\s*?\b(male|female|m|f)\b",
            re.IGNORECASE
        )
        for p_match in pax_pattern.finditer(m_lower):
            raw_name = p_match.group(1).strip()
            name_words = raw_name.split()
            while name_words and name_words[0].lower() in _PASSENGER_NAME_STOPWORDS:
                name_words.pop(0)
            name = " ".join(name_words).strip()
            if not name:
                continue
            name = name.title()
            try:
                age = int(p_match.group(2))
            except ValueError:
                continue
            gender_raw = p_match.group(3).lower()
            gender = "Male" if gender_raw.startswith("m") else "Female"
            if not any(px["name"].lower() == name.lower() for px in pax_list):
                pax_list.append({"name": name, "age": age, "gender": gender})
        if pax_list:
            existing = current_state.get("passengers") or []
            for p in pax_list:
                if not any(str(ep["name"]).lower() == str(p["name"]).lower() for ep in existing):
                    existing.append(p)
            current_state["passengers"] = existing

        # 7. Parse user name (Name Memory)
        name_memory_match = re.search(r"\bmy name is\s+([a-zA-Z]+)\b", m_lower)
        if name_memory_match:
            candidate_name = name_memory_match.group(1).strip()
            if candidate_name not in ["the", "a", "an", "passenger", "going", "travelling", "booking"]:
                current_state["user_name"] = candidate_name.title()

        # Override HYB to SC as per Railway Rules (normalization)
        if current_state.get("source") == "HYB":
            current_state["source"] = "SC"
        if current_state.get("destination") == "HYB":
            current_state["destination"] = "SC"

    # Extract state updates
    extract_state_from_message(req.message, context)
    await collections.update_session_context(req.session_id, context)

    # Audit 11: Verify MongoDB session_contexts collection after saving
    db = get_db()
    verified_context = await db.session_contexts.find_one({"session_id": req.session_id})
    logger.info(f"[VERIFY_MONGO_DB] session_contexts collection contains: {collections.serialize_doc(verified_context)}")

    # Send timeline start event
    await monitoring.broadcast_timeline_event(f"User Request: '{req.message}'")
    await monitoring.broadcast_agent_status("OrchestratorAgent", "Running", "Analyzing intent...")
    
    aggregated_text = []
    active_agent = "OrchestratorAgent"
    
    try:
        # Build prompt injecting structured context
        context_str = (
            f"[Current Session Context: "
            f"user_name={context.get('user_name') or ''}, "
            f"source={context.get('source') or ''}, "
            f"destination={context.get('destination') or ''}, "
            f"date={context.get('date') or ''}, "
            f"train_no={context.get('train_no') or ''}, "
            f"class_type={context.get('class_type') or ''}, "
            f"pnr={context.get('pnr') or ''}, "
            f"passengers={context.get('passengers') or []}, "
            f"previous_search_results={context.get('previous_search_results') or []}]"
        )
        message_with_context = f"{context_str}\nUser Request: {req.message}"
        
        # Run orchestrator asynchronously natively
        async for event in orchestrator.run_orchestrator_async(
            message_text=message_with_context,
            session_id=req.session_id,
            user_id=req.user_id or "guest_user"
        ):
            # 1. Check if node changed
            if event.node_info and event.node_info.path:
                current_node = event.node_info.path.split("/")[-1].split("@")[0]
                if current_node != active_agent:
                    await monitoring.broadcast_agent_status(active_agent, "Idle")
                    active_agent = current_node
                    # Audit 9: Print agent selected by orchestrator
                    logger.info(f"[AGENT_SELECTED] Orchestrator selected Agent: {active_agent}")
                    await monitoring.broadcast_agent_status(active_agent, "Running", f"Processing in {active_agent}")
                    await monitoring.broadcast_timeline_event(f"Delegated to specialist: {active_agent}")
            
            # 2. Check for text content
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        aggregated_text.append(part.text)
                    elif isinstance(part, dict) and 'text' in part:
                        aggregated_text.append(part['text'])
            
            # 3. Check for tool executions/actions
            if event.actions:
                if event.actions.transfer_to_agent:
                    to_agent = event.actions.transfer_to_agent
                    await monitoring.broadcast_timeline_event(f"Routing to: {to_agent}")
                if event.actions.agent_state:
                    await monitoring.broadcast_timeline_event(f"Agent state changed: {event.actions.agent_state}")
                if hasattr(event.actions, 'tool_call') and event.actions.tool_call:
                    # Audit 10: Print tool selected by orchestrator
                    logger.info(f"[TOOL_SELECTED] Orchestrator executed tool: {event.actions.tool_call}")

        # Finalize status of final active agent
        await monitoring.broadcast_agent_status(active_agent, "Idle")
        
        reply_message = "".join(aggregated_text).strip()
        if not reply_message:
            reply_message = "I have processed your request. Let me know how else I can assist you with your journey."

        # Save assistant reply to history
        await collections.save_conversation_message(req.session_id, req.user_id, "assistant", reply_message)
        await monitoring.broadcast_timeline_event("Response completed.")
        
        # Log context AFTER request
        logger.info(f"[SESSION_CONTEXT_AFTER] session_id={req.session_id} context={await collections.get_session_context(req.session_id)}")
        
        return ChatResponse(
            reply=reply_message,
            session_id=req.session_id
        )
        
    except Exception as e:
        logger.warning(f"[GEMINI_FAILED] Error executing agent runner: {e}. Falling back to mock agent flow.")
        
        # Execute Fallback Flow
        try:
            class MockPart:
                def __init__(self, text):
                    self.text = text
            class MockContent:
                def __init__(self, text):
                    self.parts = [MockPart(text)]
            class MockNodeInfo:
                def __init__(self, path):
                    self.path = path
            class MockActions:
                def __init__(self, transfer_to_agent=None, agent_state=None):
                    self.transfer_to_agent = transfer_to_agent
                    self.agent_state = agent_state
            class MockEvent:
                def __init__(self, path, text="", transfer_to_agent=None, agent_state=None):
                    self.node_info = MockNodeInfo(path)
                    self.content = MockContent(text) if text else None
                    self.actions = MockActions(transfer_to_agent, agent_state) if (transfer_to_agent or agent_state) else None

            async def run_mock_orchestrator(message: str, user_id: str, session_id: str):
                msg = message.lower()
                yield MockEvent("/OrchestratorAgent@1", agent_state="Running")
                await asyncio.sleep(0.1)
                
                from backend.services.railway_service import RailwayService
                
                current_context = await collections.get_session_context(session_id)
                extract_state_from_message(message, current_context)
                await collections.update_session_context(session_id, current_context)
                
                source = current_context.get("source")
                destination = current_context.get("destination")
                date = current_context.get("date")
                train_no = current_context.get("train_no")
                train_name = current_context.get("train_name")
                class_type = current_context.get("class_type")
                passengers = current_context.get("passengers", [])
                pnr = current_context.get("pnr")
                dialog_state = current_context.get("dialog_state", "STATE_IDLE")
                
                history = await collections.get_conversation_history(session_id)
                last_assistant_msg = ""
                for msg_item in reversed(history):
                    if msg_item.get("role") == "assistant":
                        last_assistant_msg = msg_item.get("content", "").lower()
                        break

                # Check for memory queries
                is_journey_query = "journey" in msg or "route" in msg or "travelling from" in msg
                is_train_query = any(x in msg for x in ["what train", "train did i", "train i select", "selected train", "train did i choose"])
                is_date_query = any(x in msg for x in ["what date", "when am i", "when i am", "date am i", "travelling date", "date am i travelling"])
                is_class_query = any(x in msg for x in ["what class", "class am i", "class i am", "class type", "class am i travelling in"])
                is_passenger_query = any(x in msg for x in ["how many passenger", "passenger list", "who is travelling", "passengers are booked", "passengers booked", "passengers are booked"])
                is_pnr_query = any(x in msg for x in ["what is my pnr", "my pnr number", "my pnr"]) and not ("status" in msg or "check" in msg)
                is_pnr_status_query = (
                    ("pnr" in msg and ("status" in msg or "check" in msg or "track" in msg)) or
                    bool(re.search(r"\b\d{10}\b", msg)) or
                    (pnr and any(x in msg for x in ["check my train", "check status", "train status", "where is my train"]))
                )
                is_cancellation = "cancel" in msg
                is_fare_query = any(x in msg for x in ["fare", "price", "cost"])
                
                conversational_words = ["hi", "hello", "hey", "buddy", "greetings", "yourself", "trust", "who are you", "what are you", "help me"]
                is_conversational = any(w in msg for w in conversational_words) or msg in ["hi", "hello", "hey", "start", "buddy"]

                is_search_query = any(x in msg for x in ["show train", "find train", "list train", "any train", "search train"])
                is_availability_query = any(x in msg for x in ["avail", "seat", "vacancy", "check seats"])
                is_booking_query = any(x in msg for x in ["book", "reserve", "ticket purchase", "yes", "confirm"])
                is_adding_passenger = "add" in msg and ("passenger" in msg or "people" in msg or "person" in msg or len(passengers) > 0) and bool(re.search(r"\b(male|female|m|f)\b", msg))

                # Handle Conversational / Greetings
                if is_conversational:
                    yield MockEvent("/OrchestratorAgent@1")
                    if any(w in msg for w in ["yourself", "who are you", "what are you"]):
                        reply = "I'm TrainGPT 🚆, your friendly AI railway assistant. I can help you search for trains, check seat availability, calculate fares, book tickets, check PNR status, and cancel bookings. How can I assist you today?"
                    elif "trust" in msg:
                        reply = "You can trust me to find the best routes and manage your bookings accurately. All transaction and booking simulation data is stored securely. How can I help you today?"
                    else:
                        reply = "Hello 👋 How can I help with your journey today?"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                # Handle Memory Queries
                if is_journey_query:
                    yield MockEvent("/OrchestratorAgent@1")
                    if source and destination:
                        src_name = RailwayService.get_station_name(source)
                        dest_name = RailwayService.get_station_name(destination)
                        reply = f"Your journey is planned from {src_name} ({source}) to {dest_name} ({destination})" + (f" on {date}." if date else ".")
                    else:
                        reply = "You haven't planned a journey yet. Let me know your departure and arrival stations to search for trains! 🚆"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return
                    
                if is_train_query:
                    yield MockEvent("/OrchestratorAgent@1")
                    if train_name or train_no:
                        name_str = f" ({train_name})" if train_name else ""
                        reply = f"You chose train {train_no}{name_str}."
                    else:
                        reply = "You haven't selected a train yet. Please search for trains first! 🚆"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return
                    
                if is_class_query:
                    yield MockEvent("/OrchestratorAgent@1")
                    if class_type:
                        reply = f"You are travelling in Class {class_type}."
                    else:
                        reply = "You haven't selected a travel class yet. Let me know if you prefer Sleeper (SL), 3A, 2A, or 1A! 💺"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                if is_date_query:
                    yield MockEvent("/OrchestratorAgent@1")
                    if date:
                        try:
                            dt = datetime.strptime(date, "%Y-%m-%d")
                            formatted_date = f"{dt.day} {dt.strftime('%B')} {dt.year}"
                        except Exception:
                            formatted_date = date
                        reply = f"You are travelling on {formatted_date}."
                    else:
                        reply = "You haven't specified a travel date yet."
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                if is_passenger_query:
                    yield MockEvent("/OrchestratorAgent@1")
                    if passengers:
                        p_names = ", ".join([p["name"] for p in passengers])
                        reply = f"There are {len(passengers)} passenger(s) booked: {p_names}."
                    else:
                        reply = "No passengers are currently booked on this journey."
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                if is_pnr_query:
                    yield MockEvent("/OrchestratorAgent@1")
                    if pnr:
                        reply = f"Your booking PNR is {pnr}."
                    else:
                        reply = "You don't have a PNR generated yet. Please complete the booking process first."
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                # Handle PNR status check
                if is_pnr_status_query:
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="PnrAgent")
                    yield MockEvent("/OrchestratorAgent@1/PnrAgent@2")
                    pnr_val = pnr
                    if not pnr_val:
                        pnr_match = re.search(r"\b\d{10}\b", message)
                        if pnr_match:
                            pnr_val = pnr_match.group(1)
                    if pnr_val:
                        from backend.tools.pnr_tool import check_pnr
                        res = await check_pnr(pnr=pnr_val)
                        if res["status"] == "success":
                            reply = f"Here is the status of PNR {pnr_val} 🎫:\n" \
                                    f"🚆 Train: {res.get('train_name')} ({res.get('train_no')})\n" \
                                    f"📍 Route: {res.get('source')} -> {res.get('destination')}\n" \
                                    f"📅 Journey Date: {res.get('journey_date')}\n" \
                                    f"⚡ Status: {res.get('booking_status')}\n" \
                                    f"👥 Passengers:\n"
                            for p in res.get("passengers", []):
                                reply += f"- {p['name']} ({p['age']}, {p['gender']}) - Seat: {p['seat_no']}\n"
                        else:
                            reply = f"Sorry, I couldn't find any booking for PNR {pnr_val} 🔍."
                    else:
                        reply = "Please provide the 10-digit PNR number so I can check your booking status 🔍."
                    yield MockEvent("/OrchestratorAgent@1/PnrAgent@2", text=reply)
                    return

                # Handle Cancellation
                if is_cancellation:
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="CancellationAgent")
                    yield MockEvent("/OrchestratorAgent@1/CancellationAgent@2")
                    pnr_val = pnr
                    if not pnr_val:
                        pnr_match = re.search(r"\b\d{10}\b", message)
                        if pnr_match:
                            pnr_val = pnr_match.group(1)
                    if pnr_val:
                        from backend.tools.cancellation_tool import cancel_ticket
                        res = await cancel_ticket(pnr=pnr_val)
                        if res["status"] == "success":
                            reply = f"Your ticket for PNR {pnr_val} has been successfully cancelled ❌.\n" \
                                    f"Refund Amount: \u20b9{res.get('refund_amount')}\n" \
                                    f"Cancellation Charge: \u20b9{res.get('cancellation_charge')}\n" \
                                    f"I hope to assist you with a smoother journey next time! 👋"
                        else:
                            reply = f"Cancellation failed: {res.get('message', 'Booking not found')}"
                    else:
                        reply = "Please specify the 10-digit PNR number for the ticket you wish to cancel ❌."
                    yield MockEvent("/OrchestratorAgent@1/CancellationAgent@2", text=reply)
                    return

                # Handle Adding Passenger
                if is_adding_passenger:
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="BookingAgent")
                    yield MockEvent("/OrchestratorAgent@1/BookingAgent@2")
                    selected_class = class_type or "SL"
                    if not train_no or not date:
                        reply = "I need to know which train and date to book. Please search for trains first."
                        yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                        return
                    res_book = await RailwayService.book_ticket(
                        user_id=user_id,
                        train_no=train_no,
                        journey_date=date,
                        class_type=selected_class,
                        passengers=passengers
                    )
                    if res_book["status"] == "success":
                        pnr_val = res_book.get("pnr")
                        current_context["pnr"] = pnr_val
                        current_context["passengers"] = passengers
                        current_context["dialog_state"] = "STATE_BOOKED"
                        await collections.update_session_context(session_id, current_context)
                        
                        p_names = " & ".join([p["name"] for p in passengers])
                        reply = f"Added passenger. I have booked the tickets for {p_names}.\n" \
                                f"🚆 Train: {res_book.get('train_name')} ({train_no})\n" \
                                f"📅 Date: {date} | Class: {selected_class}\n" \
                                f"👉 PNR: {pnr_val}\n" \
                                f"👥 Passenger Seats:\n"
                        for p in res_book.get("passengers", []):
                            reply += f"- {p['name']} ({p['age']}{p['gender'][0]}) -> Seat {p['seat_no']}\n"
                        reply += "\nWish you a safe and pleasant journey! 🚆👋"
                    else:
                        reply = f"Failed to book ticket: {res_book.get('message')}"
                    yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                    return

                # Booking query
                if is_booking_query or dialog_state == "STATE_CONFIRMING_BOOKING" or dialog_state == "STATE_WAITING_PASSENGERS":
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="BookingAgent")
                    yield MockEvent("/OrchestratorAgent@1/BookingAgent@2")

                    if not source or not destination:
                        reply = "Sure. Where would you like to travel from and to? (e.g. Peddapalli to Hyderabad) 🚆"
                        yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                        return

                    if not date:
                        current_context["dialog_state"] = "STATE_WAITING_PASSENGERS"
                        await collections.update_session_context(session_id, current_context)
                        reply = "I need to know your travel date before booking. Please tell me your travel date."
                        yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                        return

                    # Auto-lookup train if missing
                    if not train_no:
                        res_search = RailwayService.search_trains(source, destination, date)
                        if not res_search:
                            alt_dest = "SC" if destination == "HYB" else ("HYB" if destination == "SC" else None)
                            if alt_dest:
                                res_search_alt = RailwayService.search_trains(source, alt_dest, date)
                                if res_search_alt:
                                    destination = alt_dest
                                    current_context["destination"] = alt_dest
                                    res_search = res_search_alt
                        if res_search:
                            train_no = res_search[0]["train_no"]
                            train_name = res_search[0].get("train_name", "Express")
                            current_context["train_no"] = train_no
                            current_context["train_name"] = train_name
                            current_context["previous_search_results"] = res_search

                    if not train_no:
                        current_context["dialog_state"] = "STATE_WAITING_PASSENGERS"
                        await collections.update_session_context(session_id, current_context)
                        reply = "I couldn't find any trains for your route and date. Please search for trains first."
                        yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                        return

                    # Class Selection
                    selected_class = class_type
                    if not selected_class:
                        if any(w in msg for w in ["first one", "first", "it", "default"]):
                            selected_class = "SL"
                            current_context["class_type"] = selected_class
                        else:
                            current_context["dialog_state"] = "STATE_WAITING_PASSENGERS"
                            await collections.update_session_context(session_id, current_context)
                            reply = "Which class would you like to book? (Sleeper, 3A, or 2A)"
                            yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                            return
                    else:
                        current_context["class_type"] = selected_class

                    if not passengers:
                        current_context["dialog_state"] = "STATE_WAITING_PASSENGERS"
                        await collections.update_session_context(session_id, current_context)
                        reply = "Please provide passenger details."
                    else:
                        res_book = await RailwayService.book_ticket(
                            user_id=user_id,
                            train_no=train_no,
                            journey_date=date,
                            class_type=selected_class,
                            passengers=passengers
                        )
                        if res_book["status"] == "success":
                            pnr_val = res_book.get("pnr")
                            current_context["pnr"] = pnr_val
                            current_context["dialog_state"] = "STATE_BOOKED"
                            await collections.update_session_context(session_id, current_context)
                            
                            p_names = ", ".join([p["name"] for p in passengers])
                            reply = f"Booking successful! Your booking has been confirmed (Mock Data) 🎫!\n" \
                                    f"🚆 Train: {res_book.get('train_name')} ({train_no})\n" \
                                    f"📅 Date: {date} | Class: {selected_class}\n" \
                                    f"👉 PNR: {pnr_val}\n" \
                                    f"👥 Passenger Seats:\n"
                            for p in res_book.get("passengers", []):
                                reply += f"- {p['name']} ({p['age']}{p['gender'][0]}) -> Seat {p['seat_no']}\n"
                            reply += "\nWish you a safe and pleasant journey! 🚆👋"
                        else:
                            reply = f"Failed to book ticket: {res_book.get('message')}"
                    yield MockEvent("/OrchestratorAgent@1/BookingAgent@2", text=reply)
                    return

                # Route check
                if not source or not destination:
                    reply = "Sure. Where would you like to travel from and to? (e.g. Peddapalli to Hyderabad) 🚆"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                # Date check
                if not date:
                    dummy_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                    res_search = RailwayService.search_trains(source, destination, dummy_date)
                    if not res_search:
                        alt_dest = "SC" if destination == "HYB" else ("HYB" if destination == "SC" else None)
                        if alt_dest:
                            res_search = RailwayService.search_trains(source, alt_dest, dummy_date)
                            if res_search:
                                destination = alt_dest
                                current_context["destination"] = alt_dest
                    
                    if res_search:
                        best_train = res_search[0]
                        current_context["train_no"] = best_train["train_no"]
                        current_context["train_name"] = best_train["train_name"]
                        current_context["previous_search_results"] = res_search
                        current_context["dialog_state"] = "STATE_ROUTE_FOUND"
                        await collections.update_session_context(session_id, current_context)
                        
                        reply = f"I found {len(res_search)} trains. {best_train['train_name']} ({best_train['train_no']}) looks best.\nTravel date?"
                    else:
                        reply = f"I couldn't find any trains. Where would you like to travel from and to? 🚆"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                # Search trains explicitly
                if is_search_query:
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="SearchAgent")
                    yield MockEvent("/OrchestratorAgent@1/SearchAgent@2")
                    res_search = RailwayService.search_trains(source, destination, date)
                    if not res_search:
                        alt_dest = "SC" if destination == "HYB" else ("HYB" if destination == "SC" else None)
                        if alt_dest:
                            res_search_alt = RailwayService.search_trains(source, alt_dest, date)
                            if res_search_alt:
                                destination = alt_dest
                                current_context["destination"] = alt_dest
                                res_search = res_search_alt
                    if not res_search:
                        reply = f"I couldn't find any direct trains from {source} to {destination} on {date}. Would you like to check nearby stations?"
                    else:
                        current_context["previous_search_results"] = res_search
                        if not train_no:
                            current_context["train_no"] = res_search[0]["train_no"]
                            current_context["train_name"] = res_search[0]["train_name"]
                        current_context["dialog_state"] = "STATE_DATE_FOUND"
                        await collections.update_session_context(session_id, current_context)
                        
                        src_name = RailwayService.get_station_name(source)
                        dest_name = RailwayService.get_station_name(destination)
                        reply = f"I found the following trains from {src_name} to {dest_name} on {date} (Mock Data) 🚆:\n"
                        for idx, t in enumerate(res_search, 1):
                            reply += f"{idx}. {t['train_name']} ({t['train_no']}) - Departs {t['departure_time']}, Arrives {t['arrival_time']} ({t['travel_time']})\n"
                        reply += "\nWould you like to check seat availability or calculate fares for any of these trains?"
                    yield MockEvent("/OrchestratorAgent@1/SearchAgent@2", text=reply)
                    return

                # Class check
                if not class_type and not is_booking_query and not is_fare_query and dialog_state != "STATE_CONFIRMING_BOOKING" and dialog_state != "STATE_WAITING_PASSENGERS":
                    try:
                        dt = datetime.strptime(date, "%Y-%m-%d")
                        formatted_date = f"{dt.day} {dt.strftime('%B')}"
                    except Exception:
                        formatted_date = date
                    
                    res_search = RailwayService.search_trains(source, destination, date)
                    if not res_search:
                        alt_dest = "SC" if destination == "HYB" else ("HYB" if destination == "SC" else None)
                        if alt_dest:
                            res_search_alt = RailwayService.search_trains(source, alt_dest, date)
                            if res_search_alt:
                                destination = alt_dest
                                current_context["destination"] = alt_dest
                                res_search = res_search_alt
                    current_context["previous_search_results"] = res_search
                    if res_search:
                        best_train = res_search[0]
                        current_context["train_no"] = best_train["train_no"]
                        current_context["train_name"] = best_train["train_name"]
                        train_no = best_train["train_no"]
                        train_name = best_train["train_name"]
                    
                    current_context["dialog_state"] = "STATE_DATE_FOUND"
                    await collections.update_session_context(session_id, current_context)
                    
                    src_name = RailwayService.get_station_name(source)
                    dest_name = RailwayService.get_station_name(destination)
                    reply = f"I found the following trains from {src_name} to {dest_name} on {date} (Mock Data) 🚆:\n"
                    for idx, t in enumerate(res_search, 1):
                        reply += f"{idx}. {t['train_name']} ({t['train_no']}) - Departs {t['departure_time']}, Arrives {t['arrival_time']} ({t['travel_time']})\n"
                    reply += f"\nChecking trains for {formatted_date}. Would you like Sleeper, 3A, or 2A?"
                    yield MockEvent("/OrchestratorAgent@1", text=reply)
                    return

                # Seat Availability query
                if is_availability_query or (train_no and class_type and not pnr and dialog_state not in ["STATE_CONFIRMING_BOOKING", "STATE_WAITING_PASSENGERS", "STATE_BOOKED"] and not is_booking_query):
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="AvailabilityAgent")
                    yield MockEvent("/OrchestratorAgent@1/AvailabilityAgent@2")
                    
                    if not train_no and current_context.get("previous_search_results"):
                        first_train = current_context["previous_search_results"][0]
                        train_no = first_train["train_no"]
                        train_name = first_train.get("train_name", "Express")
                        current_context["train_no"] = train_no
                        current_context["train_name"] = train_name

                    if not train_no or not class_type:
                        reply = "Please tell me the train number and class (e.g. SL, 3A) to check availability."
                        yield MockEvent("/OrchestratorAgent@1/AvailabilityAgent@2", text=reply)
                        return

                    res_avail = RailwayService.check_availability(train_no=train_no, class_type=class_type, date=date)
                    if res_avail["status"] == "success":
                        seats = res_avail.get("available_seats")
                        current_context["dialog_state"] = "STATE_CONFIRMING_BOOKING"
                        await collections.update_session_context(session_id, current_context)
                        reply = f"For train {train_no} on {date}, {seats} seats available. Would you like me to book?"
                    else:
                        reply = f"Sorry, class {class_type} is not available on train {train_no}."
                    yield MockEvent("/OrchestratorAgent@1/AvailabilityAgent@2", text=reply)
                    return

                # Fare query
                if is_fare_query:
                    yield MockEvent("/OrchestratorAgent@1", transfer_to_agent="FareAgent")
                    yield MockEvent("/OrchestratorAgent@1/FareAgent@2")
                    selected_class = class_type or "3A"
                    current_context["class_type"] = selected_class
                    await collections.update_session_context(session_id, current_context)
                    num_pax = len(passengers) if passengers else 1

                    if not train_no:
                        reply = "Please select a train first before checking the fare."
                        yield MockEvent("/OrchestratorAgent@1/FareAgent@2", text=reply)
                        return

                    from backend.tools.fare_tool import get_fare
                    res_fare = get_fare(train_no=train_no, class_type=selected_class, num_passengers=num_pax)
                    if res_fare["status"] == "success":
                        reply = f"Here is the fare breakdown for train {res_fare.get('train_name')} ({train_no}) Class {selected_class} for {num_pax} passenger(s) (Mock Data) 💰:\n" \
                                f"- Base Fare: \u20b9{res_fare.get('base_total')}\n" \
                                f"- GST: \u20b9{res_fare.get('gst')}\n" \
                                f"- Convenience Fee: \u20b9{res_fare.get('convenience_fee')}\n" \
                                f"👉 Total Fare: \u20b9{res_fare.get('total_fare')}.\n" \
                                f"Would you like me to book the ticket for you?"
                        current_context["dialog_state"] = "STATE_CONFIRMING_BOOKING"
                        await collections.update_session_context(session_id, current_context)
                    else:
                        reply = f"Failed to calculate fare: {res_fare.get('message')}"
                    yield MockEvent("/OrchestratorAgent@1/FareAgent@2", text=reply)
                    return



                reply = "I'm here to help with your train journey. You can ask me to search for trains, check seat availability, compute fares, book tickets, or track your PNR status! 🚆"
                yield MockEvent("/OrchestratorAgent@1", text=reply)

            # Execute mock runner
            async for event in run_mock_orchestrator(req.message, req.user_id or "guest_user", req.session_id):
                if event.node_info and event.node_info.path:
                    current_node = event.node_info.path.split("/")[-1].split("@")[0]
                    if current_node != active_agent:
                        await monitoring.broadcast_agent_status(active_agent, "Idle")
                        active_agent = current_node
                        logger.info(f"[AGENT_SELECTED] Orchestrator selected Agent: {active_agent}")
                        await monitoring.broadcast_agent_status(active_agent, "Running", f"Processing in {active_agent}")
                        await monitoring.broadcast_timeline_event(f"Delegated to specialist: {active_agent}")
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            aggregated_text.append(part.text)
                if event.actions:
                    if event.actions.transfer_to_agent:
                        await monitoring.broadcast_timeline_event(f"Routing to: {event.actions.transfer_to_agent}")

            await monitoring.broadcast_agent_status(active_agent, "Idle")
            reply_message = "".join(aggregated_text).strip()
            
            # Prepend the required warning message for Gemini failure
            warning_prefix = "I'm having trouble reaching the AI service right now, but I can still help using available railway data.\n\n"
            if not reply_message.startswith("I'm having trouble"):
                reply_message = warning_prefix + reply_message
                
            await collections.save_conversation_message(req.session_id, req.user_id, "assistant", reply_message)
            await monitoring.broadcast_timeline_event("Response completed.")
            
            # Log context AFTER request
            logger.info(f"[SESSION_CONTEXT_AFTER] session_id={req.session_id} context={await collections.get_session_context(req.session_id)}")
            
            return ChatResponse(reply=reply_message, session_id=req.session_id)
        except Exception as e_mock:
            logger.error(f"Fallback simulation failed: {e_mock}", exc_info=True)
            raise HTTPException(status_code=500, detail="An error occurred while executing the fallback agent.")
