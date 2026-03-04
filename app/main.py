import json
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import models, schemas, crud
from .auth import create_access_token, decode_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth & Notifications Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- WebSocket Connection Manager ----------

class ConnectionManager:
    def __init__(self):
        # user_id -> list of WebSocket connections
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self.active.get(user_id, [])
        if ws in conns:
            conns.remove(ws)

    async def send_to_user(self, user_id: int, payload: dict):
        for ws in self.active.get(user_id, []):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                pass


manager = ConnectionManager()


# ---------- Startup ----------

@app.on_event("startup")
def startup_seed():
    db = next(get_db())
    try:
        crud.seed_users(db)
    finally:
        db.close()


# ---------- Auth ----------

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=409,
            detail="A user with that email already exists",
        )
    return crud.create_user(db, data)


@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return schemas.LoginResponse(token=token, user=user)


# ---------- Users ----------

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = crud.update_user(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------- Notifications ----------

@app.get("/notifications/{user_id}", response_model=list[schemas.NotificationResponse])
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return crud.get_notifications(db, user_id)


@app.put("/notifications/{notification_id}/read", response_model=schemas.NotificationResponse)
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    notif = crud.mark_notification_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


# ---------- WebSocket ----------

@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, userId: int, token: str, db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload or str(payload.get("sub")) != str(userId):
        await websocket.close(code=4001)
        return

    await manager.connect(userId, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(userId, websocket)


# ---------- Internal: push notification (called by other microservices) ----------

@app.post("/internal/notify")
async def push_notification(user_id: int, message: str, type: str = "INFO",
                            db: Session = Depends(get_db)):
    notif = crud.create_notification(db, user_id, message, type)
    await manager.send_to_user(user_id, {
        "type": "NOTIFICATION",
        "data": schemas.NotificationResponse.model_validate(notif).model_dump(mode="json"),
    })
    return {"message": "Notification sent"}
