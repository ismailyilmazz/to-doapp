from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import List
import os
import database
import security
import models
from datetime import date, time, timedelta 

router= APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"]
)

oAuth2_scheme= OAuth2PasswordBearer(tokenUrl="api/auth/login")

# --- HELPER FUNCTION FOR DATA CONVERSION (Kept for completeness) ---
def format_task_output(task: dict) -> dict:
    """Converts MySQL date/time objects (date, timedelta) to string format for JSON."""
    if not task:
        return task

    if task.get('dueDate') and isinstance(task['dueDate'], date):
        task['dueDate'] = task['dueDate'].isoformat()
    if task.get('dueTime'):
        if isinstance(task['dueTime'], timedelta):
            total_seconds = int(task['dueTime'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            task['dueTime'] = f"{hours:02}:{minutes:02}:{seconds:02}"
        elif isinstance(task['dueTime'], time):
             task['dueTime'] = task['dueTime'].isoformat()

    return task

def get_current_user(token: str = Depends(oAuth2_scheme)):
    # ... (get_current_user logic remains the same)
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
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to the database."
            )
            
        cursor = conn.cursor(dictionary=True) 
        query = "SELECT id, name, email FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user is None:
            raise credentials_exception
        return user       
    except JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"ERROR in get_current_user: {e}")
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
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection lost.")

        cursor = conn.cursor(dictionary=True)
        
        insert_query = """
        INSERT INTO tasks (title, description, category, status, dueDate, dueTime, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # FIX APPLIED: Ensure category is passed as None if it's empty
        params = (
            task.title, 
            task.description if task.description else None, 
            task.category if task.category else None, 
            task.status, 
            task.dueDate, 
            task.dueTime.isoformat() if task.dueTime else None,
            current_user['id']
        )
        cursor.execute(insert_query, params)
        new_task_id = cursor.lastrowid
        conn.commit() 

        select_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(select_query, (new_task_id,))
        created_task = cursor.fetchone()
        
        return format_task_output(created_task)
    except Exception as e:
        print(f"ERROR: Task Creation failed during execution or commit: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Task creation failed on server: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.get("/", response_model=List[models.Task])
def get_tasks(current_user: dict=Depends(get_current_user)):
    conn=None
    cursor=None
    try:
        conn=database.get_db_connection()
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection lost.")

        cursor=conn.cursor(dictionary=True)
        query="SELECT * FROM tasks WHERE user_id = %s"
        cursor.execute(query, (current_user['id'],))
        tasks = cursor.fetchall()
        
        return [format_task_output(task) for task in tasks]
    except Exception as e:
        print(f"ERROR in get_tasks endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
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
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection lost.")

        cursor = conn.cursor(dictionary=True)
        
        check_query = "SELECT * FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(check_query, (id, current_user['id']))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        update_query = """
        UPDATE tasks SET title=%s, description=%s, category=%s, status=%s, dueDate=%s, dueTime=%s
        WHERE id = %s AND user_id = %s
        """
        # FIX APPLIED: Ensure category is passed as None if it's empty
        params = (
            task_update.title, 
            task_update.description if task_update.description else None, 
            task_update.category if task_update.category else None, 
            task_update.status, 
            task_update.dueDate, 
            task_update.dueTime.isoformat() if task_update.dueTime else None,
            id, 
            current_user['id']
        )
        cursor.execute(update_query, params)
        conn.commit()
        
        select_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(select_query, (id,))
        updated_task = cursor.fetchone()
        
        return format_task_output(updated_task)
    except Exception as e:
        print(f"ERROR: Task Update failed during execution or commit: {e}")
        if "Task not found" in str(e):
            raise
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Task update failed on server: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int, current_user: dict = Depends(get_current_user)):
    # ... (delete_task logic remains the same)
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection lost.")

        cursor = conn.cursor()
        
        check_query = "SELECT id FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(check_query, (id, current_user['id']))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        query = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(query, (id, current_user['id']))
        conn.commit()
            
        return
    except HTTPException:
        raise 
    except Exception as e:
        print(f"ERROR: Task Deletion failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Task deletion failed on server: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/stats") 
def get_task_stats(current_user: dict = Depends(get_current_user)):
    # ... (get_task_stats logic remains the same)
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection lost.")
             
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
    except Exception as e:
        print(f"ERROR in get_task_stats endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected():
            conn.close()
