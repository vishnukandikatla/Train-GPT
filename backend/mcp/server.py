from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict
from backend.mcp.registry import TOOL_REGISTRY, get_tools_list

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol"])

class ToolCallRequest(BaseModel):
    name: str = Field(..., description="The name of the tool to execute.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Key-value arguments to pass to the tool.")

@router.get("/tools")
def list_mcp_tools():
    """
    Exposes the list of available Model Context Protocol tools.
    """
    return {
        "tools": [
            {
                "name": name,
                "description": info["description"],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        field: {"type": "string"} for field in info["input_fields"]
                    }
                }
            }
            for name, info in TOOL_REGISTRY.items()
        ]
    }

@router.post("/tools/call")
async def call_mcp_tool(req: ToolCallRequest):
    """
    Executes an MCP tool with provided arguments.
    """
    if req.name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Tool '{req.name}' not found.")

    tool_info = TOOL_REGISTRY[req.name]
    func = tool_info["func"]

    try:
        # Call the tool function. Support both async and sync tools.
        import inspect
        if inspect.iscoroutinefunction(func):
            result = await func(**req.arguments)
        else:
            result = func(**req.arguments)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing tool '{req.name}': {str(e)}")
