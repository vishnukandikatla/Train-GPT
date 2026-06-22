import time
import logging
from typing import Any, Dict, List
from backend.services.railway_service import RailwayService
from backend.database import collections

logger = logging.getLogger("traingpt.tools.search")

def search_train(source: str, destination: str, date: str) -> Dict[str, Any]:
    """
    Search for available trains between source and destination stations on a specific date.
    
    Args:
        source: Station code of departure (e.g. SBC, NDLS, SC)
        destination: Station code of arrival (e.g. SBC, NDLS, SC)
        date: Journey date in YYYY-MM-DD format (e.g. 2026-06-21)
    """
    start_time = time.time()
    try:
        logger.info(f"Running search_train tool: {source} -> {destination} on {date}")
        results = RailwayService.search_trains(source, destination, date)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log and broadcast activity
        import asyncio
        from backend.api import monitoring
        try:
            db_coro = collections.log_agent_activity(
                agent_name="Search Agent",
                tool_name="search_train",
                status="success",
                execution_time_ms=execution_time_ms,
                message=f"Found {len(results)} trains from {source} to {destination} on {date}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="search_train",
                status="success",
                execution_time=f"{execution_time_ms}ms",
                message=f"Found {len(results)} trains from {source} to {destination} on {date}"
            )
            ret_val = {
                "status": "success",
                "source": source,
                "destination": destination,
                "date": date,
                "trains": results
            }
            context_coro = collections.update_context_from_tool("search_train", {"source": source, "destination": destination, "date": date}, ret_val)
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
        except Exception as ex:
            logger.warning(f"Failed to log/broadcast agent activity: {ex}")

        return {
            "status": "success",
            "source": source,
            "destination": destination,
            "date": date,
            "trains": results
        }
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in search_train tool: {e}")
        try:
            import asyncio
            from backend.api import monitoring
            db_coro = collections.log_agent_activity(
                agent_name="Search Agent",
                tool_name="search_train",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to search trains from {source} to {destination} on {date}: {str(e)}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="search_train",
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

def recommend_train(source: str, destination: str, date: str) -> Dict[str, Any]:
    """
    Provide recommendations for the best train on a route based on shortest travel duration.
    
    Args:
        source: Station code of departure (e.g. SBC, NDLS, SC)
        destination: Station code of arrival (e.g. SBC, NDLS, SC)
        date: Journey date in YYYY-MM-DD format (e.g. 2026-06-21)
    """
    start_time = time.time()
    try:
        logger.info(f"Running recommend_train tool: {source} -> {destination} on {date}")
        results = RailwayService.recommend_trains(source, destination, date)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log and broadcast activity
        import asyncio
        from backend.api import monitoring
        try:
            db_coro = collections.log_agent_activity(
                agent_name="Search Agent",
                tool_name="recommend_train",
                status="success",
                execution_time_ms=execution_time_ms,
                message=f"Recommended {len(results)} trains from {source} to {destination}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="recommend_train",
                status="success",
                execution_time=f"{execution_time_ms}ms",
                message=f"Recommended {len(results)} trains from {source} to {destination}"
            )
            async def run_both():
                await asyncio.gather(db_coro, broadcast_coro, return_exceptions=True)

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

        return {
            "status": "success",
            "source": source,
            "destination": destination,
            "date": date,
            "recommendations": results
        }
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error in recommend_train: {e}")
        try:
            import asyncio
            from backend.api import monitoring
            db_coro = collections.log_agent_activity(
                agent_name="Search Agent",
                tool_name="recommend_train",
                status="failure",
                execution_time_ms=execution_time_ms,
                message=f"Failed to recommend trains from {source} to {destination}: {str(e)}"
            )
            broadcast_coro = monitoring.broadcast_tool_execution(
                tool_name="recommend_train",
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
