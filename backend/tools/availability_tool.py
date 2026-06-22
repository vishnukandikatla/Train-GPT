import time
import logging
from typing import Any, Dict
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.availability")

def check_availability(train_no: str, class_type: str, date: str) -> Dict[str, Any]:
    """
    Check seat availability, RAC, or Waiting List status for a specific train class and date.
    
    Args:
        train_no: Train number (e.g. 12627, 12727)
        class_type: Travel class (e.g. 1A, 2A, 3A, SL)
        date: Journey date in YYYY-MM-DD format (e.g. 2026-06-21)
    """
    start_time = time.time()
    try:
        logger.info(f"Running check_availability tool for train {train_no}, class {class_type} on {date}")
        res = RailwayService.check_availability(train_no, class_type, date)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        import asyncio
        from backend.api import monitoring
        try:
            status_msg = f"Available: {res.get('available_seats', 0)} ({res.get('seat_status', 'UNKNOWN')})" if res["status"] == "success" else res.get("message", "")
            db_coro = collections.log_agent_activity(
                agent_name="Availability Agent",
                tool_name="check_availability",
                status="success" if res["status"] == "success" else "failure",
                execution_time_ms=execution_time_ms,
                message=f"Checked availability for Train {train_no} {class_type} on {date}. {status_msg}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="check_availability",
                status="success" if res["status"] == "success" else "failure",
                execution_time=f"{execution_time_ms}ms",
                message=f"Checked availability for Train {train_no} {class_type} on {date}. {status_msg}"
            )
            context_coro = collections.update_context_from_tool("check_availability", {"train_no": train_no, "class_type": class_type, "date": date}, res)
            async def run_both():
                await asyncio.gather(db_coro, broadcast_coro, context_coro, return_exceptions=True)

            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(run_both())
                else:
                    loop.run_until_complete(run_both())
            except RuntimeError:
                asyncio.run(run_both())
        except Exception:
            pass

        return res
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in check_availability tool: {e}")
        try:
            import asyncio
            from backend.api import monitoring
            db_coro = collections.log_agent_activity(
                agent_name="Availability Agent",
                tool_name="check_availability",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to check availability: {str(e)}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="check_availability",
                status="failure",
                execution_time=f"{execution_time_ms}ms",
                message=str(e)
            )
            async def run_both_fail():
                await asyncio.gather(db_coro, broadcast_coro, return_exceptions=True)

            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(run_both_fail())
                else:
                    loop.run_until_complete(run_both_fail())
            except RuntimeError:
                asyncio.run(run_both_fail())
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
