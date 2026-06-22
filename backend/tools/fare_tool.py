import time
import logging
from typing import Any, Dict
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.fare")

def get_fare(train_no: str, class_type: str, num_passengers: int = 1) -> Dict[str, Any]:
    """
    Calculate fares, including base fare, GST, convenience fees, and total fare, for a train and class.
    
    Args:
        train_no: Train number (e.g. 12627, 12727)
        class_type: Travel class (e.g. 1A, 2A, 3A, SL)
        num_passengers: Number of passengers to calculate fare for (default: 1)
    """
    start_time = time.time()
    try:
        logger.info(f"Running get_fare tool for train {train_no}, class {class_type}, passengers {num_passengers}")
        res = RailwayService.get_fare(train_no, class_type, num_passengers)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        import asyncio
        from backend.api import monitoring
        try:
            status_msg = f"Total: Rs. {res.get('total_fare', 0)}" if res["status"] == "success" else res.get("message", "")
            db_coro = collections.log_agent_activity(
                agent_name="Fare Agent",
                tool_name="get_fare",
                status="success" if res["status"] == "success" else "failure",
                execution_time_ms=execution_time_ms,
                message=f"Calculated fare for Train {train_no} {class_type} for {num_passengers} pax. {status_msg}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="get_fare",
                status="success" if res["status"] == "success" else "failure",
                execution_time=f"{execution_time_ms}ms",
                message=f"Calculated fare for Train {train_no} {class_type} for {num_passengers} pax. {status_msg}"
            )
            context_coro = collections.update_context_from_tool(
                "get_fare",
                {"train_no": train_no, "class_type": class_type, "num_passengers": num_passengers},
                res,
                session_id=collections.current_session_id.get(None)
            )
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
        logger.error(f"Error in get_fare tool: {e}")
        try:
            import asyncio
            from backend.api import monitoring
            db_coro = collections.log_agent_activity(
                agent_name="Fare Agent",
                tool_name="get_fare",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to calculate fare: {str(e)}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="get_fare",
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
