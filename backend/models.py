from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, time

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str =Field(..., min_length=6, max_length=72)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TaskBase(BaseModel):
    title: str
    description: Optional[str]=None
    category: Optional[str] = None
    status: str="pending"
    dueDate:Optional[date]=None
    dueTime:Optional[time]=None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    pass 

class Task(TaskBase):
    id: int
    user_id: int

    class Config:
        from_attributes=True

class Token(BaseModel):
    access_token: str
    token_type:str

class TokenData(BaseModel):
    email: Optional[str]=None