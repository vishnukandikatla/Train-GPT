import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger("traingpt.monitoring")
router = APIRouter(tags=["Monitoring"])

# In-memory ring-buffer for recent API call stats (max 200 entries)
_api_call_log: List[dict] = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New dashboard client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Dashboard client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Prepare JSON string
        payload = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Failed to send to client, marking for removal: {e}")
                disconnected.append(connection)
                
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@router.websocket("/ws/agents")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep connection open and listen for optional client pings
        while True:
            data = await websocket.receive_text()
            # If client sends ping, we pong back
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)

async def broadcast_agent_status(agent_name: str, status: str, message: str = ""):
    """
    Broadcasts the state of an agent (e.g. 'Running', 'Idle').
    """
    await manager.broadcast({
        "type": "agent_status",
        "agent": agent_name,
        "status": status,
        "message": message
    })

async def broadcast_tool_execution(tool_name: str, status: str, execution_time: str, message: str):
    """
    Broadcasts tool execution events (e.g., 'search_train', 'success').
    """
    await manager.broadcast({
        "type": "tool_execution",
        "tool": tool_name,
        "status": status,
        "execution_time": execution_time,
        "message": message
    })

async def broadcast_timeline_event(message: str):
    """
    Broadcasts a log message for the real-time reasoning timeline.
    """
    time_str = datetime.now().strftime("%H:%M:%S")
    await manager.broadcast({
        "type": "timeline",
        "time": time_str,
        "message": message
    })


def record_api_call(endpoint: str, method: str, status_code: int, latency_ms: int, session_id: Optional[str] = None):
    """Record an API call in the in-memory ring buffer (thread-safe append)."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "session_id": session_id,
        "success": status_code < 400,
    }
    _api_call_log.append(entry)
    # Keep only last 200
    if len(_api_call_log) > 200:
        _api_call_log.pop(0)


# ── REST monitoring endpoints ──────────────────────────────────────────────────

@router.get("/api/monitor/logs")
async def get_monitor_logs(
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    """Return recent agent_logs from MongoDB, optionally filtered by session."""
    from backend.database import collections
    logs = await collections.get_agent_logs(limit=limit)
    if session_id:
        logs = [l for l in logs if l.get("session_id") == session_id]
    return {"status": "success", "logs": logs}


@router.get("/api/monitor/context/{session_id}")
async def get_monitor_context(session_id: str):
    """Return the current session context (memory) for a given session."""
    from backend.database import collections
    ctx = await collections.get_session_context(session_id)
    return {"status": "success", "context": ctx}


@router.get("/api/monitor/api-stats")
async def get_api_stats():
    """Return recent API call statistics from the in-memory log."""
    total = len(_api_call_log)
    success = sum(1 for c in _api_call_log if c["success"])
    avg_latency = (
        sum(c["latency_ms"] for c in _api_call_log) // total
        if total else 0
    )
    # Last 20 calls for the table
    recent = list(reversed(_api_call_log[-20:]))
    return {
        "status": "success",
        "total_calls": total,
        "success_rate": round(success / total * 100, 1) if total else 100.0,
        "avg_latency_ms": avg_latency,
        "recent": recent,
    }


@router.get("/api/monitor/sessions")
async def get_active_sessions():
    """Return recent unique session IDs from conversation history."""
    from backend.database.mongodb import get_db
    db = get_db()
    try:
        docs = await db.conversations.find(
            {}, {"session_id": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(length=20)
        sessions = [
            {"session_id": d.get("session_id"), "created_at": d.get("created_at")}
            for d in docs
        ]
    except Exception:
        sessions = []
    return {"status": "success", "sessions": sessions}
