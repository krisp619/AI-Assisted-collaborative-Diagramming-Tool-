from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import logging
from typing import List, Dict, Any
import base64
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Collaborative Whiteboard API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict, sender: WebSocket = None):
        """Broadcast message to all connected clients except sender"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            if connection != sender:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Pydantic models
class DrawingAction(BaseModel):
    type: str  # 'draw', 'clear', 'move'
    x: float
    y: float
    prevX: float = None
    prevY: float = None
    color: str = "#000000"
    lineWidth: int = 2
    timestamp: float

class AICleanupRequest(BaseModel):
    image_data: str  # base64 encoded image

class AICleanupResponse:
    def __init__(self, commands: List[Dict[str, Any]], success: bool, message: str):
        self.commands = commands
        self.success = success
        self.message = message

    def to_dict(self):
        return {
            "commands": self.commands,
            "success": self.success,
            "message": self.message
        }

@app.get("/")
async def root():
    return {"message": "Collaborative Whiteboard API is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive drawing data from client
            data = await websocket.receive_text()
            try:
                drawing_data = json.loads(data)
                logger.info(f"Received drawing data: {drawing_data.get('type', 'unknown')}")
                
                # Validate the drawing action
                action = DrawingAction(**drawing_data)
                
                # Broadcast to all other connected clients
                await manager.broadcast(drawing_data, sender=websocket)
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client")
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error processing drawing data: {e}")
                await websocket.send_text(json.dumps({
                    "error": "Error processing drawing data"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.post("/ai/cleanup", response_model=dict)
async def ai_cleanup(request: AICleanupRequest):
    """
    AI-powered diagram cleanup endpoint (Mock implementation)
    In production, this would integrate with OpenAI GPT-4o or Google Gemini.
    For this mock, we generate a simple diagram based on a fixed set of steps.
    """
    # For demonstration, let's decode the image (not used in mock)
    try:
        image_bytes = base64.b64decode(request.image_data)
    except Exception as e:
        logger.error(f"Failed to decode image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image data")

    # Mock process steps
    process_steps = ["Start", "Process", "End"]
    commands = []
    x, y = 50, 50
    width, height = 200, 100
    spacing = 50  # space between boxes

    for i, step in enumerate(process_steps):
        # Draw rectangle
        commands.append({
            "type": "rectangle",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": "#000000",
            "lineWidth": 2
        })
        # Add label inside rectangle
        commands.append({
            "type": "text",
            "x": x + width // 2,
            "y": y + height // 2 + 5,
            "text": step,
            "fontSize": 14,
            "color": "#000000"
        })

        # Draw connecting line (except after last box)
        if i < len(process_steps) - 1:
            commands.append({
                "type": "line",
                "startX": x + width,
                "startY": y + height // 2,
                "endX": x + width + spacing,
                "endY": y + height // 2,
                "color": "#000000",
                "lineWidth": 2
            })

        # Move x position for next box
        x += width + spacing

    logger.info("AI cleanup completed successfully")
    response = AICleanupResponse(commands=commands, success=True,
                                 message="Diagram cleaned successfully")
    return response.to_dict()

 
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
