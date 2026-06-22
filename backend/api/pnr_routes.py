from fastapi import APIRouter, HTTPException
from backend.services.railway_service import RailwayService

router = APIRouter(prefix="/api/pnr", tags=["PNR"])

@router.get("/{pnr}")
async def get_pnr_status(pnr: str):
    """
    Get current booking and seat allocation details for a 10-digit PNR.
    """
    res = await RailwayService.check_pnr(pnr)
    if res["status"] == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res
