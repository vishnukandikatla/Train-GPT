import time
import logging
from typing import Any, Dict
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.cancellation")

async def cancel_ticket(pnr: str) -> Dict[str, Any]:
    """
    Cancel an existing train booking using its PNR and calculate eligible refund.
    
    Args:
        pnr: The 10-digit PNR number of the booking to cancel (e.g. 1234567890)
    """
    start_time = time.time()
    try:
        logger.info(f"Running cancel_ticket tool for PNR {pnr}")
        res = await RailwayService.cancel_ticket(pnr)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        from backend.api import monitoring
        try:
            status_msg = f"Refund: Rs. {res.get('refund_amount', 0)}" if res["status"] == "success" else res.get("message", "")
            await collections.log_agent_activity(
                agent_name="Cancellation Agent",
                tool_name="cancel_ticket",
                status="success" if res["status"] == "success" else "failure",
                execution_time_ms=execution_time_ms,
                message=f"Cancelled booking for PNR {pnr}. {status_msg}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="cancel_ticket",
                status="success" if res["status"] == "success" else "failure",
                execution_time=f"{execution_time_ms}ms",
                message=f"Cancelled booking for PNR {pnr}. {status_msg}"
            )
            await collections.update_context_from_tool(
                "cancel_ticket",
                {"pnr": pnr},
                res,
                session_id=collections.current_session_id.get(None)
            )
        except Exception:
            pass

        return res
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in cancel_ticket tool: {e}")
        try:
            from backend.api import monitoring
            await collections.log_agent_activity(
                agent_name="Cancellation Agent",
                tool_name="cancel_ticket",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to cancel PNR {pnr}: {str(e)}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="cancel_ticket",
                status="failure",
                execution_time=f"{execution_time_ms}ms",
                message=str(e)
            )
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
