from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import models
import security
import database
from mysql.connector import Error as MySQLError

router= APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: models.UserCreate):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        if not conn or not conn.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to the database."
            )
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Şifreyi hashliyorum
        hashed_password = security.get_password_hash(user.password)
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
            detail=f"An unexpected server error occurred: {e}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/login", response_model=models.Token)
def login_for_access_token(form_data: models.UserLogin):
    conn=None
    cursor=None
    try:
        conn=database.get_db_connection()
        cursor=conn.cursor(dictionary=True)

        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (form_data.email,))
        user = cursor.fetchone()

        if not user or not security.verify_password(form_data.password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token=security.create_access_token(data={"sub": user['email']})
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

