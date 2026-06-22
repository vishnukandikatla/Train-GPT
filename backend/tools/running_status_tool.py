import time
import logging
from typing import Any, Dict
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.running_status")

async def train_running_status(train_no: str) -> Dict[str, Any]:
    """
    Get the live running status, delay minutes, and current location of a train.
    
    Args:
        train_no: The 5-digit train number (e.g. 12724, 12627)
    """
    start_time = time.time()
    try:
        logger.info(f"Running train_running_status tool for Train {train_no}")
        res = await RailwayService.get_running_status(train_no)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        from backend.api import monitoring
        try:
            status_msg = f"Station: {res.get('current_station', '')} | Delay: {res.get('delay_minutes', 0)} mins | Status: {res.get('message', '')}"
            await collections.log_agent_activity(
                agent_name="Search Agent",
                tool_name="train_running_status",
                status="success" if res["status"] == "success" else "failure",
                execution_time_ms=execution_time_ms,
                message=f"Checked running status of train {train_no}. {status_msg}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="train_running_status",
                status="success" if res["status"] == "success" else "failure",
                execution_time=f"{execution_time_ms}ms",
                message=f"Checked running status of train {train_no}. {status_msg}"
            )
        except Exception:
            pass

        return res
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in train_running_status tool: {e}")
        try:
            from backend.api import monitoring
            await collections.log_agent_activity(
                agent_name="Search Agent",
                tool_name="train_running_status",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to check running status of train {train_no}: {str(e)}"
            )
            await monitoring.broadcast_tool_execution(
                tool_name="train_running_status",
                status="failure",
                execution_time=f"{execution_time_ms}ms",
                message=str(e)
            )
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
