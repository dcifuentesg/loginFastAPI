from sqlalchemy.orm import Session
from . import models, schemas
from .auth import hash_password, verify_password


# ---------- User ----------

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=hash_password(user.password),
        role=user.role,
        apartment=user.apartment,
        phone=user.phone,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, data: schemas.UserUpdate):
    user = get_user(db, user_id)
    if not user:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def seed_users(db: Session):
    """Insert demo users if table is empty."""
    if db.query(models.User).count() > 0:
        return
    demo_users = [
        schemas.UserCreate(
            name="Demo Resident",
            email="resident@comunidad360.com",
            password="password123",
            role="RESIDENT",
            apartment="101",
            phone="555-0001",
        ),
        schemas.UserCreate(
            name="Admin User",
            email="admin@comunidad360.com",
            password="admin123",
            role="ADMIN",
        ),
    ]
    for u in demo_users:
        create_user(db, u)


# ---------- Notification ----------

def get_notifications(db: Session, user_id: int):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


def get_notification(db: Session, notification_id: int):
    return db.query(models.Notification).filter(models.Notification.id == notification_id).first()


def mark_notification_read(db: Session, notification_id: int):
    notif = get_notification(db, notification_id)
    if notif:
        notif.read = True
        db.commit()
        db.refresh(notif)
    return notif


def create_notification(db: Session, user_id: int, message: str, notif_type: str = "INFO"):
    notif = models.Notification(user_id=user_id, message=message, type=notif_type)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
