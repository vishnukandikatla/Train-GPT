from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from backend.services.railway_service import RailwayService
from backend.database import collections

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])

class PassengerSchema(BaseModel):
    name: str
    age: int
    gender: str

class BookingRequest(BaseModel):
    train_no: str
    journey_date: str
    class_type: str
    passengers: List[PassengerSchema]
    user_id: Optional[str] = "guest_user"

@router.post("")
async def create_booking(req: BookingRequest):
    """
    Directly book a train ticket with passenger names.
    """
    passengers_list = [p.model_dump() for p in req.passengers]
    res = await RailwayService.book_ticket(
        user_id=req.user_id,
        train_no=req.train_no,
        journey_date=req.journey_date,
        class_type=req.class_type,
        passengers=passengers_list
    )
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@router.get("")
async def get_bookings(user_id: Optional[str] = "guest_user", all_bookings: bool = False):
    """
    Get bookings list. If all_bookings is true, lists all system bookings (for admin/analytics).
    """
    if all_bookings:
        bookings = await collections.get_all_bookings()
    else:
        user_id_str = user_id or "guest_user"
        bookings = await collections.get_user_bookings(user_id_str)
    return {"status": "success", "bookings": bookings}

@router.delete("/{pnr}")
async def cancel_booking(pnr: str):
    """
    Cancel booking by PNR and process refund.
    """
    res = await RailwayService.cancel_ticket(pnr)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res
