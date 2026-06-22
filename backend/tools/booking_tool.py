import time
import logging
from typing import Any, Dict, List, Optional
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.booking")

async def book_ticket(
    train_no: str,
    journey_date: str,
    class_type: str,
    passengers: List[Dict[str, Any]],
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Book a train ticket for a set of passengers, allocating seat numbers and generating a PNR.
    
    Args:
        train_no: Train number (e.g. 12627, 12727)
        journey_date: Date of travel in YYYY-MM-DD format (e.g. 2026-06-21)
        class_type: Travel class (e.g. 1A, 2A, 3A, SL)
        passengers: List of passengers, where each passenger is a dict with keys: 'name' (str), 'age' (int/str), and 'gender' (str)
        user_id: Optional user identifier (system-provided if authenticated)
    """
    start_time = time.time()
    try:
        logger.info(f"Running book_ticket tool for train {train_no}, class {class_type}, passengers {passengers}")
        res = await RailwayService.book_ticket(user_id, train_no, journey_date, class_type, passengers)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        from backend.api import monitoring
        try:
            status_msg = f"PNR: {res.get('pnr', '')} ({res.get('booking_status', '')})" if res["status"] == "success" else res.get("message", "")
            await collections.log_agent_activity(
                agent_name="Booking Agent",
                tool_name="book_ticket",
                status="success" if res["status"] == "success" else "failure",
                execution_time_ms=execution_time_ms,
                message=f"Booked ticket on Train {train_no} {class_type} for {len(passengers)} pax. {status_msg}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="book_ticket",
                status="success" if res["status"] == "success" else "failure",
                execution_time=f"{execution_time_ms}ms",
                message=f"Booked ticket on Train {train_no} {class_type} for {len(passengers)} pax. {status_msg}"
            )
            await collections.update_context_from_tool(
                "book_ticket",
                {"train_no": train_no, "journey_date": journey_date, "class_type": class_type, "passengers": passengers, "user_id": user_id},
                res,
                session_id=collections.current_session_id.get(None)
            )
        except Exception:
            pass

        return res
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in book_ticket tool: {e}")
        try:
            from backend.api import monitoring
            await collections.log_agent_activity(
                agent_name="Booking Agent",
                tool_name="book_ticket",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to book ticket: {str(e)}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="book_ticket",
                status="failure",
                execution_time=f"{execution_time_ms}ms",
                message=str(e)
            )
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
