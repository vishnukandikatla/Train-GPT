import os
import json
import random
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from backend.database import collections
from backend.services.railway_provider import RailwayProvider, _load_json, _save_json, TRAINS_FILE, STATIONS_FILE, AVAILABILITY_FILE

logger = logging.getLogger("traingpt.railway_service")

class RailwayService:
    @staticmethod
    def get_stations() -> List[Dict[str, str]]:
        return _load_json(STATIONS_FILE, [])

    @staticmethod
    def get_station_name(code: str) -> str:
        stations = RailwayService.get_stations()
        for s in stations:
            if s["code"].upper() == code.upper():
                return s["name"]
        return code

    @staticmethod
    def search_trains(source: str, destination: str, date: str) -> List[Dict[str, Any]]:
        return RailwayProvider.search_trains(source, destination, date)

    @staticmethod
    def recommend_trains(source: str, destination: str, date: str) -> List[Dict[str, Any]]:
        trains = RailwayService.search_trains(source, destination, date)
        def parse_travel_time(t_str):
            try:
                parts = t_str.split()
                hours = int(parts[0].replace("h", ""))
                mins = int(parts[1].replace("m", "")) if len(parts) > 1 else 0
                return hours * 60 + mins
            except Exception:
                return 9999
        
        sorted_trains = sorted(trains, key=lambda x: parse_travel_time(x["travel_time"]))
        return sorted_trains

    @staticmethod
    def check_availability(train_no: str, class_type: str, date: str) -> Dict[str, Any]:
        return RailwayProvider.check_availability(train_no, class_type, date)

    @staticmethod
    def get_fare(train_no: str, class_type: str, num_passengers: int = 1) -> Dict[str, Any]:
        return RailwayProvider.get_fare(train_no, class_type, num_passengers)

    @staticmethod
    async def book_ticket(
        user_id: Optional[str],
        train_no: str,
        journey_date: str,
        class_type: str,
        passengers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # 1. Verify train and class
        trains = _load_json(TRAINS_FILE, [])
        target_train = None
        for t in trains:
            if t["train_no"] == train_no:
                target_train = t
                break
        
        if not target_train:
            return {"status": "error", "message": f"Train {train_no} not found."}

        # 2. Check seat availability
        avail = RailwayService.check_availability(train_no, class_type, journey_date)
        if avail["status"] == "error":
            return avail

        available_seats = avail["available_seats"]
        num_passengers = len(passengers)
        
        booking_status = "Confirmed"
        assigned_passengers = []
        
        # Determine starting coach and seat numbers
        random.seed(datetime.now(timezone.utc).timestamp())
        coach_prefix = "B" if class_type == "3A" else ("A" if class_type == "2A" else ("H" if class_type == "1A" else "S"))
        coach_no = random.randint(1, 4)
        start_seat = random.randint(1, 60)
        
        # 3. Update availability in local file
        availability_data = _load_json(AVAILABILITY_FILE, {})
        
        if available_seats >= num_passengers:
            new_available = available_seats - num_passengers
            if journey_date in availability_data and train_no in availability_data[journey_date] and class_type in availability_data[journey_date][train_no]:
                availability_data[journey_date][train_no][class_type]["available"] = new_available
                availability_data[journey_date][train_no][class_type]["status"] = "AVAILABLE" if new_available > 0 else "WL-1"
                _save_json(AVAILABILITY_FILE, availability_data)
            
            for idx, p in enumerate(passengers):
                seat_no = f"{coach_prefix}{coach_no}/{start_seat + idx}"
                assigned_passengers.append({
                    "name": p["name"],
                    "age": int(p["age"]),
                    "gender": p["gender"],
                    "seat_no": seat_no
                })
        else:
            current_status = avail["seat_status"]
            wl_start = 1
            if current_status.startswith("WL-"):
                try:
                    wl_start = int(current_status.split("-")[1])
                except Exception:
                    pass
            
            booking_status = "Waitlisted"
            if journey_date in availability_data and train_no in availability_data[journey_date] and class_type in availability_data[journey_date][train_no]:
                availability_data[journey_date][train_no][class_type]["available"] = 0
                availability_data[journey_date][train_no][class_type]["status"] = f"WL-{wl_start + num_passengers}"
                _save_json(AVAILABILITY_FILE, availability_data)
            
            for idx, p in enumerate(passengers):
                seat_no = f"WL/{wl_start + idx}"
                assigned_passengers.append({
                    "name": p["name"],
                    "age": int(p["age"]),
                    "gender": p["gender"],
                    "seat_no": seat_no
                })

        # 4. Generate 10-digit PNR
        pnr = "".join([str(random.randint(0, 9)) for _ in range(10)])

        # 5. Create Booking in DB
        booking = await collections.create_booking(
            user_id=user_id,
            pnr=pnr,
            train_no=train_no,
            train_name=target_train["train_name"],
            source=target_train["source"],
            destination=target_train["destination"],
            journey_date=journey_date,
            class_type=class_type,
            passengers=assigned_passengers,
            status=booking_status
        )

        return {
            "status": "success",
            "pnr": pnr,
            "booking_id": booking["_id"],
            "train_no": train_no,
            "train_name": target_train["train_name"],
            "source": target_train["source"],
            "destination": target_train["destination"],
            "journey_date": journey_date,
            "class_type": class_type,
            "booking_status": booking_status,
            "passengers": booking["passengers"],
            "data_source": "mock"
        }

    @staticmethod
    async def check_pnr(pnr: str) -> Dict[str, Any]:
        # 1. Try checking live PNR APIs
        res = RailwayProvider.get_pnr_status(pnr)
        if res and res.get("status") == "success":
            return res

        # 2. Fall back to local MongoDB records
        booking = await collections.get_booking_by_pnr(pnr)
        if not booking:
            return {"status": "error", "message": f"PNR {pnr} not found."}
        
        return {
            "status": "success",
            "pnr": pnr,
            "train_no": booking["train_no"],
            "train_name": booking["train_name"],
            "source": booking["source"],
            "destination": booking["destination"],
            "journey_date": booking["journey_date"],
            "class_type": booking["class_type"],
            "booking_status": booking["status"],
            "booking_time": booking["booking_time"],
            "passengers": booking.get("passengers", []),
            "data_source": "mock"
        }

    @staticmethod
    async def get_running_status(train_no: str) -> Dict[str, Any]:
        return RailwayProvider.get_running_status(train_no)

    @staticmethod
    async def cancel_ticket(pnr: str) -> Dict[str, Any]:
        booking = await collections.get_booking_by_pnr(pnr)
        if not booking:
            return {"status": "error", "message": f"PNR {pnr} not found."}

        if booking["status"] == "Cancelled":
            return {"status": "error", "message": f"PNR {pnr} is already cancelled."}

        class_type = booking["class_type"]
        base_fares = RailwayService.get_fare(booking["train_no"], class_type, len(booking.get("passengers", [])))
        
        total_paid = base_fares.get("total_fare", 0) if base_fares["status"] == "success" else 500
        cancellation_charge = 240 if class_type in ["1A", "2A"] else 120
        refund_amount = max(0, total_paid - cancellation_charge)

        await collections.update_booking_status(pnr, "Cancelled")

        journey_date = booking["journey_date"]
        train_no = booking["train_no"]
        num_passengers = len(booking.get("passengers", []))
        
        availability_data = _load_json(AVAILABILITY_FILE, {})
        if journey_date in availability_data and train_no in availability_data[journey_date]:
            class_avail = availability_data[journey_date][train_no].get(class_type)
            if class_avail and class_avail["status"] == "AVAILABLE":
                class_avail["available"] += num_passengers
                _save_json(AVAILABILITY_FILE, availability_data)

        return {
            "status": "success",
            "pnr": pnr,
            "refund_amount": refund_amount,
            "cancellation_charge": cancellation_charge,
            "message": "Ticket cancelled successfully.",
            "data_source": "mock"
        }
