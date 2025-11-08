from fastapi import APIRouter, HTTPException, status, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm 
import models
import security
import database
from mysql.connector import Error as MySQLError

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)


def is_connection_alive(conn):
    try:
        if hasattr(conn, "is_connected"):
            return conn.is_connected()
        conn.execute("SELECT 1")
        return True
    except Exception:
        return False


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: models.UserCreate):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        if not conn or not is_connection_alive(conn):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to the database."
            )

        if hasattr(conn, "cursor"):
            try:
                cursor = conn.cursor(dictionary=True)
            except TypeError:
                cursor = conn.cursor()
        else:
            raise HTTPException(status_code=500, detail="Invalid database connection.")

        query = "SELECT * FROM users WHERE email = ?"
        if hasattr(conn, "is_connected"):
            query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_password = security.get_password_hash(user.password)
        insert_query = "INSERT INTO users (name, email, password) VALUES (?, ?, ?)"
        if hasattr(conn, "is_connected"):
            insert_query = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (user.name, user.email, hashed_password))
        conn.commit()

        return {"message": f"User '{user.name}' was created successfully."}

    except HTTPException:
        raise
    except MySQLError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {err}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected server error: {e}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn and is_connection_alive(conn):
            conn.close()


@router.post("/login", response_model=models.Token)
def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...)
): 
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        if hasattr(conn, "cursor"):
            try:
                cursor = conn.cursor(dictionary=True)
            except TypeError:
                cursor = conn.cursor()
        else:
            raise HTTPException(status_code=500, detail="Invalid database connection.")

        query = "SELECT * FROM users WHERE email = ?"
        if hasattr(conn, "is_connected"): 
            query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if isinstance(user, tuple):
            cols = [col[0] for col in cursor.description]
            user = dict(zip(cols, user))

        if not security.verify_password(password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = security.create_access_token(data={"sub": user['email']})
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn and is_connection_alive(conn):
            conn.close()