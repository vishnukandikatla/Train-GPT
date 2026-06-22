from typing import Any, Callable, Dict, List
from backend.tools.search_tool import search_train, recommend_train
from backend.tools.availability_tool import check_availability
from backend.tools.fare_tool import get_fare
from backend.tools.booking_tool import book_ticket
from backend.tools.pnr_tool import check_pnr
from backend.tools.cancellation_tool import cancel_ticket

from backend.tools.running_status_tool import train_running_status

# Central registry of tool definitions
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "search_train": {
        "func": search_train,
        "description": "Search for trains between source and destination stations on a specific date.",
        "input_fields": ["source", "destination", "date"]
    },
    "recommend_train": {
        "func": recommend_train,
        "description": "Recommend trains based on shortest travel duration on a route.",
        "input_fields": ["source", "destination", "date"]
    },
    "check_availability": {
        "func": check_availability,
        "description": "Check seat availability and RAC/Waiting List status for a train and class on a date.",
        "input_fields": ["train_no", "class_type", "date"]
    },
    "get_fare": {
        "func": get_fare,
        "description": "Calculate travel fare breakdown for a train, class, and number of passengers.",
        "input_fields": ["train_no", "class_type", "num_passengers"]
    },
    "book_ticket": {
        "func": book_ticket,
        "description": "Book ticket(s) for list of passengers on a train and class.",
        "input_fields": ["train_no", "journey_date", "class_type", "passengers"]
    },
    "check_pnr": {
        "func": check_pnr,
        "description": "Track current status and booking details of a train ticket using the 10-digit PNR.",
        "input_fields": ["pnr"]
    },
    "cancel_ticket": {
        "func": cancel_ticket,
        "description": "Cancel a booking using PNR and calculate refund details.",
        "input_fields": ["pnr"]
    },
    "train_running_status": {
        "func": train_running_status,
        "description": "Get the live running status, delay minutes, and current location of a train.",
        "input_fields": ["train_no"]
    }
}


def get_tools_list() -> List[Dict[str, Any]]:
    return [
        {
            "name": name,
            "description": info["description"],
            "input_fields": info["input_fields"]
        }
        for name, info in TOOL_REGISTRY.items()
    ]
