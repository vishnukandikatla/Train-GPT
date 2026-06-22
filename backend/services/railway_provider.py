import os
import time
import json
import logging
import requests
import random
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("traingpt.railway_provider")

# Data File Paths
MOCK_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mock_data")
TRAINS_FILE = os.path.join(MOCK_DATA_DIR, "trains.json")
STATIONS_FILE = os.path.join(MOCK_DATA_DIR, "stations.json")
AVAILABILITY_FILE = os.path.join(MOCK_DATA_DIR, "availability.json")

def _load_json(file_path: str, default: Any = None) -> Any:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
    return default or []

def _save_json(file_path: str, data: Any):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")

class RailwayProvider:
    @staticmethod
    def rapidapi_get(host: str, endpoint: str, params: dict, retries: int = 2) -> Optional[Dict[str, Any]]:
        api_key = os.getenv("RAILWAY_API_KEY")
        if not api_key:
            logger.warning("RAILWAY_API_KEY is not configured in settings. Skipping external API call.")
            return None

        url = f"https://{host}{endpoint}"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": host
        }

        for attempt in range(1, retries + 1):
            start_time = time.time()
            try:
                logger.info(f"API Request: GET {url} | Host: {host} | Attempt: {attempt}/{retries}")
                response = requests.get(url, headers=headers, params=params, timeout=5)
                duration_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"API Response: {response.status_code} | Host: {host} | Time: {duration_ms}ms")
                
                if response.status_code == 429:
                    logger.warning(f"Rate limit exceeded (429) for host: {host}")
                    return {"_status_code": 429}
                
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        if isinstance(res_json, dict):
                            res_json["_status_code"] = 200
                        return res_json
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response from {host}: {e}")
                        return None
                        
                # Log non-200 / non-429 status codes
                logger.warning(f"Received status code {response.status_code} from host: {host}")
            except requests.Timeout:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"Timeout ({duration_ms}ms) reached on attempt {attempt} for host: {host}")
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Error calling {host} on attempt {attempt}: {e} (duration: {duration_ms}ms)")
                
        return None

    @classmethod
    def search_trains(cls, source: str, destination: str, date: str) -> List[Dict[str, Any]]:
        providers = [
            os.getenv("RAILWAY_SEARCH_HOST") or "irctc1.p.rapidapi.com",
            "indian-railway-irctc.p.rapidapi.com",
            "irctc-api2.p.rapidapi.com"
        ]
        
        params = {
            "fromStationCode": source,
            "toStationCode": destination,
            "date": date
        }

        for host in providers:
            res = cls.rapidapi_get(host=host, endpoint="/api/v3/trainBetweenStations", params=params)
            if res and res.get("_status_code") == 200:
                trains = []
                data_list = res.get("data") or res.get("trains") or []
                if not isinstance(data_list, list) and isinstance(res.get("data"), dict):
                    data_list = res["data"].get("trains") or []
                
                for item in data_list:
                    # Resilient key mapping
                    train_no = item.get("train_number") or item.get("train_no") or item.get("trainNo") or item.get("number")
                    train_name = item.get("train_name") or item.get("trainName") or item.get("name")
                    src = item.get("from_station") or item.get("fromStation") or item.get("source") or item.get("from")
                    dest = item.get("to_station") or item.get("toStation") or item.get("destination") or item.get("to")
                    dep_time = item.get("from_std") or item.get("departure_time") or item.get("departureTime") or "00:00"
                    arr_time = item.get("to_std") or item.get("arrival_time") or item.get("arrivalTime") or "00:00"
                    duration = item.get("duration") or item.get("travel_time") or "00h 00m"
                    runs = item.get("run_days") or item.get("runs_on") or ["Daily"]
                    
                    if train_no and train_name:
                        trains.append({
                            "train_no": str(train_no),
                            "train_name": str(train_name),
                            "source": str(src or source),
                            "destination": str(dest or destination),
                            "departure_time": str(dep_time),
                            "arrival_time": str(arr_time),
                            "travel_time": str(duration),
                            "runs_on": runs,
                            "classes": ["1A", "2A", "3A", "SL"],
                            "base_fares": {
                                "1A": 2200,
                                "2A": 1500,
                                "3A": 1100,
                                "SL": 450
                            },
                            "data_source": "live"
                        })
                if trains:
                    return trains
                    
            elif res and res.get("_status_code") == 429:
                logger.warning(f"Search failover: Host {host} returned 429. Trying next provider.")
                continue

        logger.info("All live Search API providers failed or returned rate limits. Falling back to Mock Data.")
        return cls._mock_search_trains(source, destination, date)

    @classmethod
    def check_availability(cls, train_no: str, class_type: str, date: str) -> Dict[str, Any]:
        if str(train_no) == "12704":
            train_no = "12724"
        elif str(train_no) == "12703":
            train_no = "12723"
        providers = [
            os.getenv("RAILWAY_AVAILABILITY_HOST") or "indian-railway-seat-availability.p.rapidapi.com",
            "rail-info-api-indial.p.rapidapi.com"
        ]

        params = {
            "trainNo": train_no,
            "classType": class_type,
            "date": date
        }

        for host in providers:
            res = cls.rapidapi_get(host=host, endpoint="/api/v1/seatAvailability", params=params)
            if res and res.get("_status_code") == 200:
                # Resilient key parsing
                avail_seats = res.get("available_seats") or res.get("available") or res.get("seats")
                seat_status = res.get("seat_status") or res.get("status") or "AVAILABLE"
                
                if avail_seats is not None:
                    return {
                        "status": "success",
                        "train_no": train_no,
                        "class_type": class_type,
                        "date": date,
                        "available_seats": int(avail_seats),
                        "seat_status": str(seat_status),
                        "data_source": "live"
                    }
            elif res and res.get("_status_code") == 429:
                logger.warning(f"Availability failover: Host {host} returned 429. Trying next provider.")
                continue

        logger.info("All live Availability API providers failed. Falling back to Mock Data.")
        return cls._mock_check_availability(train_no, class_type, date)

    @classmethod
    def get_pnr_status(cls, pnr: str) -> Dict[str, Any]:
        providers = [
            os.getenv("RAILWAY_PNR_HOST") or "irctc-indian-railway-pnr-status.p.rapidapi.com",
            "pnr-status-indian-railway.p.rapidapi.com",
            "real-time-pnr-status-api-for-indian-railways.p.rapidapi.com"
        ]

        params = {"pnr": pnr}

        for host in providers:
            res = cls.rapidapi_get(host=host, endpoint="/api/v1/pnrStatus", params=params)
            if res and res.get("_status_code") == 200:
                # Resilient parsing
                data = res.get("data") or res
                train_no = data.get("train_no") or data.get("train_number") or data.get("trainNo")
                train_name = data.get("train_name") or data.get("trainName")
                src = data.get("source") or data.get("from") or data.get("from_station")
                dest = data.get("destination") or data.get("to") or data.get("to_station")
                journey_date = data.get("journey_date") or data.get("date") or data.get("dateOfJourney")
                class_type = data.get("class_type") or data.get("class") or data.get("travel_class")
                booking_status = data.get("booking_status") or data.get("status") or "Confirmed"
                
                passengers_raw = data.get("passengers") or []
                passengers = []
                for p in passengers_raw:
                    name = p.get("name") or "Passenger"
                    age = p.get("age") or 30
                    gender = p.get("gender") or "Male"
                    seat = p.get("seat_no") or p.get("berth") or "CNF"
                    passengers.append({
                        "name": str(name),
                        "age": int(age),
                        "gender": str(gender),
                        "seat_no": str(seat)
                    })

                if train_no:
                    return {
                        "status": "success",
                        "pnr": pnr,
                        "train_no": str(train_no),
                        "train_name": str(train_name or "Express"),
                        "source": str(src or "SC"),
                        "destination": str(dest or "NDLS"),
                        "journey_date": str(journey_date or "2026-06-24"),
                        "class_type": str(class_type or "3A"),
                        "booking_status": str(booking_status),
                        "passengers": passengers,
                        "data_source": "live"
                    }
            elif res and res.get("_status_code") == 429:
                logger.warning(f"PNR Status failover: Host {host} returned 429. Trying next provider.")
                continue

        logger.info("All live PNR API providers failed. Checking local MongoDB/mock records.")
        return {"status": "error", "message": "PNR check failed on all live APIs"}

    @classmethod
    def get_running_status(cls, train_no: str) -> Dict[str, Any]:
        if str(train_no) == "12704":
            train_no = "12724"
        elif str(train_no) == "12703":
            train_no = "12723"
        providers = [
            os.getenv("RAILWAY_RUNNING_HOST") or "train-running-api.p.rapidapi.com"
        ]

        params = {"trainNo": train_no}

        for host in providers:
            res = cls.rapidapi_get(host=host, endpoint="/api/v1/runningStatus", params=params)
            if res and res.get("_status_code") == 200:
                current_station = res.get("current_station") or res.get("last_station") or "SC"
                delay = res.get("delay") or res.get("delay_minutes") or 0
                msg = res.get("status") or res.get("message") or "Running on time"
                
                return {
                    "status": "success",
                    "train_no": train_no,
                    "current_station": str(current_station),
                    "delay_minutes": int(delay),
                    "message": str(msg),
                    "data_source": "live"
                }
            elif res and res.get("_status_code") == 429:
                logger.warning(f"Running Status failover: Host {host} returned 429. Trying next provider.")
                continue

        logger.info("All live Running Status API providers failed. Returning mock running status.")
        return cls._mock_get_running_status(train_no)

    @classmethod
    def get_fare(cls, train_no: str, class_type: str, num_passengers: int = 1) -> Dict[str, Any]:
        if str(train_no) == "12704":
            train_no = "12724"
        elif str(train_no) == "12703":
            train_no = "12723"
        # Standard fare calculation wrapper
        trains = _load_json(TRAINS_FILE, [])
        target_train = None
        for t in trains:
            if t["train_no"] == train_no:
                target_train = t
                break

        if not target_train:
            return {"status": "error", "message": f"Train {train_no} not found."}

        base_fares = target_train.get("base_fares", {})
        base_fare = base_fares.get(class_type) or 450
        base_total = base_fare * num_passengers
        
        irctc_charge = 15
        gst = int(base_total * 0.05) if class_type in ["1A", "2A", "3A"] else 0
        total_fare = base_total + irctc_charge + gst

        return {
            "status": "success",
            "train_no": train_no,
            "train_name": target_train["train_name"],
            "class_type": class_type,
            "num_passengers": num_passengers,
            "base_fare_per_passenger": base_fare,
            "base_total": base_total,
            "gst": gst,
            "convenience_fee": irctc_charge,
            "total_fare": total_fare,
            "data_source": "mock"
        }

    # ================= MOCK FALLBACKS =================
    @staticmethod
    def _mock_search_trains(source: str, destination: str, date: str) -> List[Dict[str, Any]]:
        trains = _load_json(TRAINS_FILE, [])
        matching_trains = []
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_of_week = date_obj.strftime("%a")
        except Exception:
            day_of_week = None

        for t in trains:
            if t["source"].upper() == source.upper() and t["destination"].upper() == destination.upper():
                if day_of_week is None or day_of_week in t["runs_on"]:
                    t_copy = t.copy()
                    t_copy["data_source"] = "mock"
                    matching_trains.append(t_copy)
        return matching_trains

    @staticmethod
    def _mock_check_availability(train_no: str, class_type: str, date: str) -> Dict[str, Any]:
        availability_data = _load_json(AVAILABILITY_FILE, {})
        trains = _load_json(TRAINS_FILE, [])
        train_exists = any(t["train_no"] == train_no for t in trains)
        if not train_exists:
            return {"status": "error", "message": f"Train {train_no} not found."}

        if date not in availability_data:
            availability_data[date] = {}

        if train_no not in availability_data[date]:
            random.seed(f"{train_no}-{date}")
            availability_data[date][train_no] = {
                "1A": { "available": random.randint(0, 10), "status": "AVAILABLE" },
                "2A": { "available": random.randint(0, 25), "status": "AVAILABLE" },
                "3A": { "available": random.randint(0, 50), "status": "AVAILABLE" },
                "SL": { "available": random.randint(0, 120), "status": "AVAILABLE" }
            }
            for c, detail in availability_data[date][train_no].items():
                if detail["available"] == 0:
                    wl_no = random.randint(1, 15)
                    detail["status"] = f"WL-{wl_no}"
            _save_json(AVAILABILITY_FILE, availability_data)

        train_avail = availability_data[date][train_no]
        if class_type not in train_avail:
            return {"status": "error", "message": f"Class {class_type} not available on Train {train_no}."}
            
        return {
            "status": "success",
            "train_no": train_no,
            "class_type": class_type,
            "date": date,
            "available_seats": train_avail[class_type]["available"],
            "seat_status": train_avail[class_type]["status"],
            "data_source": "mock"
        }

    @staticmethod
    def _mock_get_running_status(train_no: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "train_no": train_no,
            "current_station": "SC",
            "delay_minutes": 10,
            "message": "Running late by 10 minutes (Mock Data)",
            "data_source": "mock"
        }
