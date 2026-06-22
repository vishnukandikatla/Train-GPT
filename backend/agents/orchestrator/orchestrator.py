import os
import logging
from typing import Any, Dict, Generator, AsyncGenerator
from dotenv import load_dotenv

# Import Google ADK modules
from google.adk import Agent, Runner, Event
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import tools
from backend.tools.search_tool import search_train, recommend_train
from backend.tools.availability_tool import check_availability
from backend.tools.fare_tool import get_fare
from backend.tools.booking_tool import book_ticket
from backend.tools.pnr_tool import check_pnr
from backend.tools.cancellation_tool import cancel_ticket
from backend.tools.running_status_tool import train_running_status

# Load env variables
load_dotenv()

logger = logging.getLogger("traingpt.orchestrator")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Define specialized worker agents
search_agent = Agent(
    name="SearchAgent",
    description="Railway Search Specialist. Helps users find train routes and recommends best options.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT's Railway Search Specialist 🚆. "
        "Your role is to help users find train routes and schedules. "
        "Use 'search_train' to look up train schedules and 'recommend_train' to find shortest duration journeys. "
        "Use 'train_running_status' to look up real-time delays and station status of trains. "
        "Always be friendly, helpful, conversational, and use emojis. "
        "State clearly whether the data is (Live Data) or (Mock Data) based on the returned 'data_source'. "
        "If you cannot fulfill the request, ask the user for details or refer them to another action naturally without mentioning internal agents."
    ),
    tools=[search_train, recommend_train, train_running_status]
)

availability_agent = Agent(
    name="AvailabilityAgent",
    description="Railway Seat Availability Specialist. Checks available seats and WL/RAC statuses.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT's Seat Availability Specialist 💺. "
        "Your role is to check seat availability for a train, class, and journey date. "
        "Use 'check_availability' to check available seats. "
        "Present availability, RAC, or Waiting List counts clearly. "
        "Always state clearly that availability details are (Mock Data) as per the returned tool metadata. "
        "If the user wishes to proceed with booking or fare checks, suggest it naturally without mentioning internal system names."
    ),
    tools=[check_availability]
)

fare_agent = Agent(
    name="FareAgent",
    description="Railway Fare Specialist. Calculates ticket price breakdown and taxes.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT's Fare Specialist 💰. "
        "Your role is to calculate travel fares and convenience fees. "
        "Use 'get_fare' to compute pricing details for a train class and passenger count. "
        "Provide a clear, friendly breakdown (Base Fare, GST, Convenience Fee, and Total). "
        "Always state clearly that the fare is (Mock Data) as returned by the tool."
    ),
    tools=[get_fare]
)

booking_agent = Agent(
    name="BookingAgent",
    description="Railway Ticket Booking Specialist. Collects passenger details and generates PNR.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT's Ticket Booking Specialist 🎫. "
        "Your role is to guide the user through booking their ticket. "
        "To book, you need: 1. Train Number, 2. Journey Date, 3. Travel Class (e.g. 1A, 2A, 3A, SL), "
        "and 4. Passenger Details (Name, Age, Gender for each passenger). "
        "Prompt the user step-by-step for any missing details. "
        "Once you have all required parameters, execute the 'book_ticket' tool. "
        "Confirm the booking status (Confirmed or Waitlisted), PNR, and allocated coach/seat numbers. "
        "Clearly state that the booking is confirmed/waitlisted (Mock Data)."
    ),
    tools=[book_ticket]
)

pnr_agent = Agent(
    name="PnrAgent",
    description="Railway PNR Tracker. Tracks live itinerary, confirmation status, and passenger list.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT's PNR Specialist 🔍. "
        "Your role is to check and display active booking itineraries using the 10-digit PNR. "
        "Use the 'check_pnr' tool to load the ticket status, train details, and passenger seats. "
        "Present details cleanly, warmly, and use emojis. Clearly state this is (Mock Data)."
    ),
    tools=[check_pnr]
)

cancellation_agent = Agent(
    name="CancellationAgent",
    description="Railway Ticket Cancellation Specialist. Handles cancellations, seat release, and refund calculations.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT's Cancellation Specialist ❌. "
        "Your role is to assist with ticket cancellations. "
        "Use the 'cancel_ticket' tool to cancel bookings using the 10-digit PNR. "
        "Confirm cancellation, refund amount, and fees in a helpful, polite tone. Clearly state this is (Mock Data)."
    ),
    tools=[cancel_ticket]
)

# Define the parent coordinator Orchestrator agent
orchestrator_agent = Agent(
    name="OrchestratorAgent",
    description="Main TrainGPT AI Coordinator. Routes user query to appropriate specialized sub-agents.",
    model=MODEL_NAME,
    instruction=(
        "You are TrainGPT, a friendly conversational AI railway assistant 🚆. "
        "Your role is to assist users warmly and naturally from search to booking. "
        "NEVER mention internal terms like 'coordinator agent', 'SearchAgent', 'BookingAgent', 'Orchestrator', or any tool/function names/execution details. "
        "NEVER expose technical details. "
        "Adopt a welcoming and helpful tone. E.g.: "
        "- Start with: 'Hello 👋 How can I help with your journey today?' "
        "- If route is searched: 'I found trains for your trip 🚆' "
        "- If availability is checked: 'Let me check seat availability.' "
        "- If booking is completed: 'Your booking has been confirmed 🎫' "
        "Always maintain conversation context. Do not ask for details the user has already provided."
    ),
    sub_agents=[
        search_agent,
        availability_agent,
        fare_agent,
        booking_agent,
        pnr_agent,
        cancellation_agent
    ]
)

# Global session service for agent conversations
session_service = InMemorySessionService()

def run_orchestrator(
    message_text: str,
    session_id: str,
    user_id: str = "guest_user"
) -> Generator[Event, None, None]:
    """
    Executes the Orchestrator Agent flow for a given session.
    """
    runner = Runner(
        agent=orchestrator_agent,
        session_service=session_service,
        app_name="TrainGPT",
        auto_create_session=True,
    )
    
    # Wrap standard text prompt in google-genai Content structure
    new_message = types.Content(
        parts=[types.Part.from_text(text=message_text)]
    )
    
    # Generator execution
    yield from runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message
    )

async def run_orchestrator_async(
    message_text: str,
    session_id: str,
    user_id: str = "guest_user"
) -> AsyncGenerator[Event, None]:
    """
    Executes the Orchestrator Agent flow asynchronously for a given session.
    """
    runner = Runner(
        agent=orchestrator_agent,
        session_service=session_service,
        app_name="TrainGPT",
        auto_create_session=True,
    )
    
    # Wrap standard text prompt in google-genai Content structure
    new_message = types.Content(
        parts=[types.Part.from_text(text=message_text)]
    )
    
    # Async Generator execution
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message
    ):
        yield event
