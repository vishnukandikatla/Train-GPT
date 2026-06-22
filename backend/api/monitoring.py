import json
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("traingpt.monitoring")
router = APIRouter(tags=["Monitoring"])

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
    from datetime import datetime
    time_str = datetime.now().strftime("%H:%M:%S")
    await manager.broadcast({
        "type": "timeline",
        "time": time_str,
        "message": message
    })
