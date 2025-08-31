from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import logging
from typing import List, Dict, Any
import base64


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Diagramming Tool", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db = {
    "demo@example.com": "password123"
}


# -------------------- MODELS --------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str


class DrawingAction(BaseModel):
    type: str
    x: float
    y: float
    prevX: float = None
    prevY: float = None
    color: str = "#000000"
    lineWidth: int = 2
    timestamp: float

class AICleanupRequest(BaseModel):
    image_data: str

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


# -------------------- CONNECTION MANAGER --------------------
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

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# -------------------- WEBSOCKETS --------------------
@app.websocket("/ws/draw")
async def websocket_draw(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                drawing_data = json.loads(data)
                await manager.broadcast(drawing_data, sender=websocket)
            except json.JSONDecodeError:
                print("⚠️ Received non-JSON:", data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                drawing_data = json.loads(data)
                action = DrawingAction(**drawing_data)
                await manager.broadcast(drawing_data, sender=websocket)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                logger.error(f"Error processing drawing data: {e}")
                await websocket.send_text(json.dumps({"error": "Error processing drawing data"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# -------------------- ROUTES --------------------
@app.get("/")
async def home_page():
    return FileResponse("static/index.html")

@app.post("/register")
async def register_user(user: RegisterRequest):
    if user.email in users_db:
        return {"success": False, "message": "Email already registered!"}
    users_db[user.email] = user.password
    return {"success": True, "message": "Registration successful! Please login."}

@app.post("/login")
async def login_user(user: LoginRequest):
    if user.email not in users_db or users_db[user.email] != user.password:
        return {"success": False, "message": "Invalid email or password!"}
    return {"success": True, "message": "Login successful!"}

@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")

@app.get("/register")
async def register_page():
    return FileResponse("static/register.html")


@app.post("/ai/cleanup", response_model=dict)
async def ai_cleanup(request: AICleanupRequest):
    try:
        base64.b64decode(request.image_data)
    except Exception as e:
        logger.error(f"Failed to decode image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image data")

    process_steps = ["Start", "Process", "End"]
    commands = []
    x, y = 50, 50
    width, height = 200, 100
    spacing = 50

    for i, step in enumerate(process_steps):
        commands.append({
            "type": "rectangle",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": "#000000",
            "lineWidth": 2
        })
        commands.append({
            "type": "text",
            "x": x + width // 2,
            "y": y + height // 2 + 5,
            "text": step,
            "fontSize": 14,
            "color": "#000000"
        })
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
        x += width + spacing

    return AICleanupResponse(commands=commands, success=True,
                             message="Diagram cleaned successfully").to_dict()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_connections": len(manager.active_connections)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
