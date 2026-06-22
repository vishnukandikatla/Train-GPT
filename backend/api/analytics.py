from fastapi import APIRouter
from backend.database import collections
from backend.services.railway_service import RailwayService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("")
async def get_analytics():
    """
    Get live analytics summary and agent activity logs.
    """
    # 1. Fetch real agent logs from database
    logs = await collections.get_agent_logs(limit=20)
    
    # 2. Query database for real booking counts
    db_bookings = await collections.get_all_bookings()
    bookings_count = len(db_bookings)
    
    # 3. Compute stats from real activity logs
    search_logs = [log for log in logs if log.get("tool_name") == "search_train"]
    total_searches = len(search_logs)
    
    # Unique users based on actual bookings
    unique_users = len(set(b.get("user_id") for b in db_bookings if b.get("user_id")))

    # 4. Generate train popularity data for ECharts chart from real bookings
    popularity = {}
    for b in db_bookings:
        t_name = b.get("train_name", "Unknown")
        popularity[t_name] = popularity.get(t_name, 0) + 1

    # Seed popularity chart if no bookings yet (demo mode)
    if not popularity:
        popularity = {
            "Karnataka Express": 0,
            "Telangana Express": 0,
            "Rajdhani Express": 0,
            "Godavari Express": 0
        }

    popularity_data = [{"name": name, "value": count} for name, count in popularity.items()]

    return {
        "status": "success",
        "stats": {
            "bookings_today": bookings_count,
            "search_requests": total_searches,
            "active_users": unique_users,
            "active_agents": 6
        },
        "popularity_data": popularity_data,
        "logs": [
            {
                "id": str(log.get("_id", "")),
                "agent_name": log.get("agent_name"),
                "tool_name": log.get("tool_name"),
                "status": log.get("status"),
                "execution_time": log.get("execution_time"),
                "message": log.get("message"),
                "timestamp": log.get("timestamp")
            }
            for log in logs
        ]
    }
