import contextvars
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, overload
from backend.database.mongodb import get_db

current_session_id: contextvars.ContextVar[Any] = contextvars.ContextVar("current_session_id", default=None)

@overload
def serialize_doc(doc: None) -> None: ...

@overload
def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]: ...

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize_doc(doc) for doc in docs]

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    res = await db.users.find_one({"email": email})
    return serialize_doc(res)

async def create_user(name: str, email: str, password_hash: str) -> Dict[str, Any]:
    db = get_db()
    user = {
        "name": name,
        "email": email,
        "password": password_hash,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    res = await db.users.insert_one(user)
    user["_id"] = str(res.inserted_id)
    return user

async def get_booking_by_pnr(pnr: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    booking = await db.bookings.find_one({"pnr": pnr})
    if booking:
        booking = serialize_doc(booking)
        # Load passengers for this booking
        cursor = db.passengers.find({"booking_id": str(booking["_id"])})
        passengers = await cursor.to_list()
        booking["passengers"] = serialize_docs(passengers)
    return booking

async def create_booking(
    user_id: Optional[str],
    pnr: str,
    train_no: str,
    train_name: str,
    source: str,
    destination: str,
    journey_date: str,
    class_type: str,
    passengers: List[Dict[str, Any]],
    status: str = "Confirmed"
) -> Dict[str, Any]:
    db = get_db()
    booking: Dict[str, Any] = {
        "user_id": user_id,
        "pnr": pnr,
        "train_no": train_no,
        "train_name": train_name,
        "source": source,
        "destination": destination,
        "journey_date": journey_date,
        "class_type": class_type,
        "status": status,
        "booking_time": datetime.now(timezone.utc).isoformat()
    }
    res = await db.bookings.insert_one(booking)
    booking_id = str(res.inserted_id)
    booking["_id"] = booking_id

    # Insert passengers
    saved_passengers = []
    for idx, p in enumerate(passengers):
        passenger_doc = {
            "booking_id": booking_id,
            "name": p["name"],
            "age": p["age"],
            "gender": p["gender"],
            "seat_no": p.get("seat_no", f"Coach-B{idx+1}/Seat-{10+idx*2}")
        }
        p_res = await db.passengers.insert_one(passenger_doc)
        passenger_doc["_id"] = str(p_res.inserted_id)
        saved_passengers.append(passenger_doc)

    booking["passengers"] = saved_passengers
    return booking

async def get_user_bookings(user_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.bookings.find({"user_id": user_id})
    bookings = await cursor.to_list()
    serialized = []
    for booking in bookings:
        b = serialize_doc(booking)
        p_cursor = db.passengers.find({"booking_id": str(b["_id"])})
        passengers = await p_cursor.to_list()
        b["passengers"] = serialize_docs(passengers)
        serialized.append(b)
    return serialized

async def get_all_bookings() -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.bookings.find({})
    bookings = await cursor.to_list()
    serialized = []
    for booking in bookings:
        b = serialize_doc(booking)
        p_cursor = db.passengers.find({"booking_id": str(b["_id"])})
        passengers = await p_cursor.to_list()
        b["passengers"] = serialize_docs(passengers)
        serialized.append(b)
    return serialized

async def update_booking_status(pnr: str, status: str) -> bool:
    db = get_db()
    res = await db.bookings.update_one({"pnr": pnr}, {"$set": {"status": status}})
    return res.modified_count > 0

async def log_agent_activity(
    agent_name: str,
    tool_name: Optional[str],
    status: str,
    execution_time_ms: int,
    message: str
) -> Dict[str, Any]:
    db = get_db()
    log = {
        "agent_name": agent_name,
        "tool_name": tool_name,
        "status": status,
        "execution_time": f"{execution_time_ms}ms",
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.agent_logs.insert_one(log)
    return log

async def get_agent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.agent_logs.find({})
    logs = await cursor.to_list(length=limit)
    serialized = serialize_docs(logs)
    # Sort logs by timestamp descending locally if needed
    serialized.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return serialized

async def get_conversation_history(session_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    history = await db.conversations.find_one({"session_id": session_id})
    if history:
        return history.get("messages", [])
    return []

async def save_conversation_message(session_id: str, user_id: Optional[str], role: str, content: str):
    db = get_db()
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check if conversation document exists
    doc = await db.conversations.find_one({"session_id": session_id})
    if doc:
        await db.conversations.update_one(
            {"session_id": session_id},
            {"$push": {"messages": message}}
        )
    else:
        new_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": [message],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(new_doc)

async def get_session_context(session_id: str) -> Dict[str, Any]:
    db = get_db()
    doc = await db.session_contexts.find_one({"session_id": session_id})
    if doc:
        doc = serialize_doc(doc)
    else:
        doc = {}
    
    # Ensure current_trip is populated in response
    trip = doc.get("current_trip") or {}
    current_trip = {
        "source": doc.get("source") or trip.get("source"),
        "destination": doc.get("destination") or trip.get("destination"),
        "date": doc.get("date") or trip.get("date"),
        "train_no": doc.get("train_no") or trip.get("train_no"),
        "train_name": doc.get("train_name") or trip.get("train_name"),
        "class_type": doc.get("class_type") or trip.get("class_type"),
        "passengers": doc.get("passengers") or trip.get("passengers") or [],
        "pnr": doc.get("pnr") or trip.get("pnr")
    }
    
    # Merge/standardize all expected fields
    return {
        "session_id": session_id,
        "source": current_trip["source"],
        "destination": current_trip["destination"],
        "date": current_trip["date"],
        "train_no": current_trip["train_no"],
        "train_name": current_trip["train_name"],
        "class_type": current_trip["class_type"],
        "passengers": current_trip["passengers"],
        "pnr": current_trip["pnr"],
        "previous_search_results": doc.get("previous_search_results") or [],
        "dialog_state": doc.get("dialog_state") or "STATE_IDLE",
        "current_trip": current_trip,
        "user_name": doc.get("user_name")
    }

async def update_session_context(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    current = await get_session_context(session_id)
    
    # Normalize updates
    normalized_updates = {}
    for k, v in updates.items():
        normalized_updates[k] = v
        if k == "journey_date":
            normalized_updates["date"] = v
            
    # Synchronize updates to both top-level and current_trip
    for k, v in normalized_updates.items():
        if k in ["session_id", "_id", "current_trip"]:
            continue
        # Only apply non-None updates to avoid wiping existing values
        if v is not None:
            current[k] = v
            if k in current.get("current_trip", {}):
                current["current_trip"][k] = v
                
    if "current_trip" in updates and isinstance(updates["current_trip"], dict):
        for k, v in updates["current_trip"].items():
            if v is not None and k not in normalized_updates:
                current[k] = v
                current["current_trip"][k] = v
            
    # Save back to MongoDB
    set_fields = {}
    for k, v in current.items():
        if k in ["session_id", "_id"]:
            continue
        # Do not persist None values back into the document
        if v is not None:
            set_fields[k] = v
            
    await db.session_contexts.update_one(
        {"session_id": session_id},
        {"$set": set_fields},
        upsert=True
    )
    return current

async def update_context_from_tool(tool_name: str, inputs: Dict[str, Any], output: Dict[str, Any], session_id: Optional[str] = None):
    """
    Update session context based on a tool execution.

    Prefer an explicit `session_id` argument (safe when callers pass it).
    Fall back to the `current_session_id` ContextVar only when not provided.
    """
    if not session_id:
        session_id = current_session_id.get(None)
    if not session_id:
        return
        
    updates = {}
    if tool_name == "search_train":
        if output.get("status") == "success":
            updates["source"] = output.get("source")
            updates["destination"] = output.get("destination")
            updates["date"] = output.get("date")
            trains = output.get("trains", [])
            updates["previous_search_results"] = trains
            if trains:
                updates["train_no"] = trains[0]["train_no"]
                updates["train_name"] = trains[0]["train_name"]
    elif tool_name == "check_availability":
        if output.get("status") == "success":
            updates["train_no"] = output.get("train_no")
            updates["class_type"] = output.get("class_type")
            updates["date"] = output.get("date")
    elif tool_name == "get_fare":
        if output.get("status") == "success":
            updates["train_no"] = output.get("train_no")
            updates["class_type"] = output.get("class_type")
    elif tool_name == "book_ticket":
        if output.get("status") == "success":
            updates["train_no"] = output.get("train_no")
            updates["journey_date"] = output.get("journey_date")
            updates["class_type"] = output.get("class_type")
            updates["passengers"] = output.get("passengers", [])
            updates["pnr"] = output.get("pnr")
    elif tool_name == "check_pnr":
        if output.get("status") == "success":
            updates["pnr"] = output.get("pnr")
            updates["train_no"] = output.get("train_no")
            updates["journey_date"] = output.get("journey_date")
            updates["class_type"] = output.get("class_type")
            updates["passengers"] = output.get("passengers", [])
    elif tool_name == "cancel_ticket":
        if output.get("status") == "success":
            updates["pnr"] = output.get("pnr")
            
    if updates:
        await update_session_context(session_id, updates)


