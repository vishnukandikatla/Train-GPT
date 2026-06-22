import time
import logging
from typing import Any, Dict
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.pnr")

async def check_pnr(pnr: str) -> Dict[str, Any]:
    """
    Check the current status and passenger details of a train booking using the 10-digit PNR.
    
    Args:
        pnr: The 10-digit PNR number of the booking (e.g. 1234567890)
    """
    start_time = time.time()
    try:
        logger.info(f"Running check_pnr tool for PNR {pnr}")
        res = await RailwayService.check_pnr(pnr)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        from backend.api import monitoring
        try:
            status_msg = f"Status: {res.get('booking_status', '')}" if res["status"] == "success" else res.get("message", "")
            await collections.log_agent_activity(
                agent_name="PNR Agent",
                tool_name="check_pnr",
                status="success" if res["status"] == "success" else "failure",
                execution_time_ms=execution_time_ms,
                message=f"Checked PNR {pnr}. {status_msg}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="check_pnr",
                status="success" if res["status"] == "success" else "failure",
                execution_time=f"{execution_time_ms}ms",
                message=f"Checked PNR {pnr}. {status_msg}"
            )
            await collections.update_context_from_tool("check_pnr", {"pnr": pnr}, res)
        except Exception:
            pass

        return res
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in check_pnr tool: {e}")
        try:
            from backend.api import monitoring
            await collections.log_agent_activity(
                agent_name="PNR Agent",
                tool_name="check_pnr",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to check PNR {pnr}: {str(e)}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="check_pnr",
                status="failure",
                execution_time=f"{execution_time_ms}ms",
                message=str(e)
            )
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
