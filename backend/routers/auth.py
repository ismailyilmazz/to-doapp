from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import database, models, security
from datetime import timedelta
from typing import List

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login") Burayı değiştirdim ama geri gelebilir şimdilik böyle kalsın
security_scheme = HTTPBearer()

# Bu fonksiyonu tasks.py ve files.py da kullanacak, o yüzden burada tanımlı olması önemli.
def get_current_user(token: HTTPAuthorizationCredentials = Depends(security_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    conn = None
    cursor = None
    try:
        token_str = token.credentials
        payload = jwt.decode(token_str, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        conn = database.get_db_connection()
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=503, detail="Database connection failed")
             
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT id, name, email, role FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user is None:
            raise credentials_exception
            
        return user 

    except JWTError:
        raise credentials_exception
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: models.UserCreate):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = security.get_password_hash(user.password)
        
        # Yeni kullanıcıyı ekle (role varsayılan olarak 'user' gidecek veritabanı ayarından dolayı)
        # Ama biz yine de kodda belirtelim, ileride admin kaydı açarsak burayı değiştiririz.
        insert_query = "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (user.name, user.email, hashed_password, "user")) 
        conn.commit()
        
        return {"message": "User created successfully"}
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.post("/login", response_model=models.Token)
def login_for_access_token(user_login: models.UserLogin):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (user_login.email,))
        user = cursor.fetchone()
        
        if not user or not security.verify_password(user_login.password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        access_token = security.create_access_token(
            data={"sub": user['email'], "role": user['role']}, 
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "role": user['role'] 
        }
        
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.get("/users", response_model=List[models.User])
def get_all_users(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
        
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, email, role FROM users")
        users = cursor.fetchall()
        return users
    finally:
        cursor.close()
        conn.close()