from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
import models
import schemas
from auth import get_password_hash

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_tasks(db: Session, user_id: int, skip: int = 0, limit: int = 100,
             sort_by: str = None, sort_order: str = "asc",
             search: str = None, status: str = None):
    query = db.query(models.Task).filter(models.Task.owner_id == user_id)
    
    if search:
        query = query.filter(or_(
            models.Task.title.ilike(f"%{search}%"),
            models.Task.description.ilike(f"%{search}%")
        ))
    if status:
        query = query.filter(models.Task.status == status)
    
    if sort_by:
        field = getattr(models.Task, sort_by, models.Task.created_at)
        query = query.order_by(desc(field) if sort_order == "desc" else asc(field))
    
    return query.offset(skip).limit(limit).all()

def get_top_priority_tasks(db: Session, user_id: int, n: int = 5):
    return db.query(models.Task)\
             .filter(models.Task.owner_id == user_id)\
             .order_by(models.Task.priority.desc())\
             .limit(n)\
             .all()

def create_user_task(db: Session, task: schemas.TaskCreate, user_id: int):
    db_task = models.Task(**task.dict(), owner_id=user_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task
