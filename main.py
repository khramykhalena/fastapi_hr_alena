from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from datetime import timedelta
from typing import List, Optional

import models, schemas, crud, auth
from database import engine, get_db
from dependencies import get_current_user
from config import settings

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(settings.REDIS_URL)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

@app.post("/register/", response_model=schemas.User)
def register(user: schemas.UserCreate, db=Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/tasks/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db=Depends(get_db), 
               current_user: schemas.User = Depends(get_current_user)):
    return crud.create_user_task(db=db, task=task, user_id=current_user.id)

@app.get("/tasks/", response_model=List[schemas.Task])
@cache(expire=30)
def read_tasks(skip: int = 0, limit: int = 100, sort_by: str = None, 
              sort_order: str = "asc", search: str = None, status: str = None,
              db=Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.get_tasks(db, user_id=current_user.id, skip=skip, limit=limit,
                        sort_by=sort_by, sort_order=sort_order,
                        search=search, status=status)

@app.get("/tasks/top_priority/", response_model=List[schemas.Task])
@cache(expire=30)
def read_top_priority_tasks(n: int = 5, db=Depends(get_db),
                          current_user: schemas.User = Depends(get_current_user)):
    return crud.get_top_priority_tasks(db, user_id=current_user.id, n=n)
