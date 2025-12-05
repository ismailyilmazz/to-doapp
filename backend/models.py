from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, time, datetime

class Attachment(BaseModel):
    id: int
    task_id: int
    original_name: str
    file_path: str
    file_size: int
    upload_date: datetime
    uploader_id: int

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str =Field(..., min_length=6, max_length=72)
    role: str = "user" # Varsayılan olarak 'user' rolü, yeni geldi bu :)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str # YENİ GELDİ BU :)

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str]=None
    category: Optional[str] = None
    status: str="pending"
    dueDate:Optional[date]=None
    dueTime:Optional[time]=None
    assigned_to: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    pass 

class Task(TaskBase):
    id: int
    user_id: int
    attachments: List[Attachment] = [] # Yeni geldi :)
    
    class Config:
        from_attributes=True

class Token(BaseModel):
    access_token: str
    token_type:str
    role: str  # YENİ GELDİ BU :)

class TokenData(BaseModel):
    email: Optional[str]=None
    role: Optional[str] = None  # YENİ GELDİ BU :)