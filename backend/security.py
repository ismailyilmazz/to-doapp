from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from typing import Optional
from datetime import timedelta, timezone, datetime
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "aeaiwaglargjeiaoghaergs")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

try:
  
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
except ValueError:
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") #Hashleyerek dbye kaydediyorum,bcrypt ile değişebilir?

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data:dict, expires_delta: Optional[timedelta]=None):
    to_encode = data.copy()
    if expires_delta:
        expire=datetime.now(timezone.utc)+expires_delta
    else:
        # Use the cleaned ACCESS_TOKEN_EXPIRE_MINUTES variable
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
