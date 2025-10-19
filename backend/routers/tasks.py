from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import List
import os
import database
import security
import models

router= APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"]
)

oAuth2_scheme= OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oAuth2_scheme)):
    """
    Token'ı çözer ve mevcut kullanıcıyı veritabanından getirir.
    Bu fonksiyon, korumalı endpoint'lerde bir bağımlılık olarak kullanılacak.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    conn = None
    cursor = None
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception

        conn = database.get_db_connection()
        if not conn or not conn.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to the database."
            )
            
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, name, email FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user is None:
            # Token geçerli ama kullanıcı DB'de yoksa
            raise credentials_exception
        return user       
    except JWTError:
        raise credentials_exception
    except Exception:
        raise credentials_exception
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.post("/", response_model=models.Task, status_code=status.HTTP_201_CREATED)
def create_task(task: models.TaskCreate, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        insert_query = """
        INSERT INTO tasks (title, description, category, status, dueDate, dueTime, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (task.title, task.description, task.category, task.status, task.dueDate, task.dueTime, current_user['id'])
        cursor.execute(insert_query, params)
        new_task_id = cursor.lastrowid
        conn.commit()        
        # Oluşturulan görevi veritabanından geri oku ve döndür
        select_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(select_query, (new_task_id,))
        created_task = cursor.fetchone()
        
        return created_task
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.get("/", response_model=List[models.Task])
def get_tasks(current_user: dict=Depends(get_current_user)):
    conn=None
    cursor=None
    try:
        conn=database.get_db_connection()
        cursor=conn.cursor(dictionary=True)
        query="SELECT * FROM tasks WHERE user_id = %s"
        cursor.execute(query, (current_user['id'],))
        tasks = cursor.fetchall()
        return tasks
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.put("/{id}", response_model=models.Task)
def update_task(id: int, task_update: models.TaskUpdate, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        check_query = "SELECT * FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(check_query, (id, current_user['id']))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_44_NOT_FOUND, detail="Task not found")
        
        update_query = """
        UPDATE tasks SET title=%s, description=%s, category=%s, status=%s, dueDate=%s, dueTime=%s
        WHERE id = %s AND user_id = %s
        """
        params = (task_update.title, task_update.description, task_update.category, task_update.status, task_update.dueDate, task_update.dueTime, id, current_user['id'])
        cursor.execute(update_query, params)
        conn.commit()
        #güncel görev
        select_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(select_query, (id,))
        updated_task = cursor.fetchone()
        
        return updated_task
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(query, (id, current_user['id']))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            
        return
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.get("/stats") #değişebilir
def get_task_stats(current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT 
            category,
            status,
            COUNT(*) as count
        FROM tasks 
        WHERE user_id = %s
        GROUP BY category, status
        """
        cursor.execute(query, (current_user['id'],))
        stats = cursor.fetchall()
        
        # İstatistikleri daha kullanışlı bir formata dönüştürelim
        formatted_stats = {}
        for row in stats:
            category = row['category'] if row['category'] else 'Uncategorized'
            if category not in formatted_stats:
                formatted_stats[category] = {'completed': 0, 'incomplete': 0}
            
            if row['status'] == 'completed':
                formatted_stats[category]['completed'] += row['count']
            else: # pending, in_progress
                formatted_stats[category]['incomplete'] += row['count']
        
        return formatted_stats
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
