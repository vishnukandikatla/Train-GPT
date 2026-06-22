from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.services.railway_service import RailwayService

router = APIRouter(prefix="/api/trains", tags=["Trains"])

class TrainSearchRequest(BaseModel):
    source: str
    destination: str
    date: str # YYYY-MM-DD

class AvailabilityRequest(BaseModel):
    train_no: str
    class_type: str
    date: str

class FareRequest(BaseModel):
    train_no: str
    class_type: str
    num_passengers: int = 1

@router.get("/stations")
def get_stations():
    """
    Get lists of all active stations.
    """
    return RailwayService.get_stations()

@router.post("/search")
def search_trains(req: TrainSearchRequest):
    """
    Search for trains on a route for a specific date.
    """
    trains = RailwayService.search_trains(req.source, req.destination, req.date)
    return {"status": "success", "trains": trains}

@router.post("/availability")
def check_availability(req: AvailabilityRequest):
    """
    Check seat availability for a train, class, and date.
    """
    res = RailwayService.check_availability(req.train_no, req.class_type, req.date)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@router.post("/fare")
def calculate_fare(req: FareRequest):
    """
    Calculate fare details for a train class and passenger count.
    """
    res = RailwayService.get_fare(req.train_no, req.class_type, req.num_passengers)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res
