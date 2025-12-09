from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import database
import models
from datetime import date, time, timedelta 
from routers.auth import get_current_user 
import os

router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"]
)

def format_task_output(task: dict) -> dict:
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

@router.post("/", response_model=models.Task, status_code=status.HTTP_201_CREATED)
def create_task(task: models.TaskCreate, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        if not conn or not conn.is_connected():
             raise HTTPException(status_code=503, detail="Database connection lost.")

        cursor = conn.cursor(dictionary=True)
        
        user_id_to_save = current_user['id']
        assigned_to_id = None
        
        if current_user['role'] == 'admin' and task.assigned_to:
            assigned_to_id = task.assigned_to

        insert_query = """
        INSERT INTO tasks (title, description, category, status, dueDate, dueTime, user_id, assigned_to)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            task.title, 
            task.description if task.description else None, 
            task.category if task.category else None, 
            task.status, 
            task.dueDate, 
            task.dueTime.isoformat() if task.dueTime else None,
            user_id_to_save,
            assigned_to_id
        )
        cursor.execute(insert_query, params)
        new_task_id = cursor.lastrowid
        conn.commit() 

        select_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(select_query, (new_task_id,))
        created_task = cursor.fetchone()
        
        created_task['attachments'] = []
        
        return format_task_output(created_task)
    except Exception as e:
        print(f"ERROR: Task Creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Task creation failed: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.get("/", response_model=List[models.Task])
def get_tasks(current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if current_user['role'] == 'admin':
            query = "SELECT * FROM tasks"
            cursor.execute(query)
        else:
            query = "SELECT * FROM tasks WHERE user_id = %s OR assigned_to = %s"
            cursor.execute(query, (current_user['id'], current_user['id']))
            
        tasks = cursor.fetchall()
        
        for task in tasks:
            cursor.execute("SELECT * FROM attachments WHERE task_id = %s", (task['id'],))
            task['attachments'] = cursor.fetchall()
            format_task_output(task)
            
        return tasks
    except Exception as e:
        print(f"ERROR in get_tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.put("/{id}", response_model=models.Task)
def update_task(id: int, task_update: models.TaskUpdate, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        check_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(check_query, (id,))
        existing_task = cursor.fetchone()
        
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")

        if current_user['role'] != 'admin':
            if existing_task['user_id'] != current_user['id'] and existing_task['assigned_to'] != current_user['id']:
                 raise HTTPException(status_code=403, detail="Not authorized to update this task")
            
        if current_user['role'] != 'admin':
            task_update.assigned_to = existing_task['assigned_to']
        
        update_query = """
        UPDATE tasks SET title=%s, description=%s, category=%s, status=%s, dueDate=%s, dueTime=%s, assigned_to=%s
        WHERE id = %s
        """
        params = (
            task_update.title, 
            task_update.description, 
            task_update.category, 
            task_update.status, 
            task_update.dueDate, 
            task_update.dueTime.isoformat() if task_update.dueTime else None,
            task_update.assigned_to,
            id
        )
        cursor.execute(update_query, params)
        conn.commit()
        
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
        updated_task = cursor.fetchone()
        
        cursor.execute("SELECT * FROM attachments WHERE task_id = %s", (id,))
        updated_task['attachments'] = cursor.fetchall()
        
        return format_task_output(updated_task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        check_query = "SELECT * FROM tasks WHERE id = %s"
        cursor.execute(check_query, (id,))
        task = cursor.fetchone()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if current_user['role'] != 'admin' and task['user_id'] != current_user['id']:
             raise HTTPException(status_code=403, detail="Not authorized to delete this task")

        # Dosyaları diskten silme işlemi
        cursor.execute("SELECT file_path FROM attachments WHERE task_id = %s", (id,))
        attachments = cursor.fetchall()
        for attachment in attachments:
            if os.path.exists(attachment['file_path']):
                try:
                    os.remove(attachment['file_path'])
                except Exception as e:
                    print(f"Dosya silinemedi: {e}") 

        query = "DELETE FROM tasks WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()
        return
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@router.get("/stats") 
def get_task_stats(current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if current_user['role'] == 'admin':
             query = """
                SELECT category, status, COUNT(*) as count
                FROM tasks 
                GROUP BY category, status
            """
             cursor.execute(query)
        else:
            query = """
                SELECT category, status, COUNT(*) as count
                FROM tasks 
                WHERE user_id = %s OR assigned_to = %s
                GROUP BY category, status
            """
            cursor.execute(query, (current_user['id'], current_user['id']))
            
        stats = cursor.fetchall()
        
        formatted_stats = {}
        for row in stats:
            category = row['category'] if row['category'] else 'Uncategorized'
            if category not in formatted_stats:
                formatted_stats[category] = {'completed': 0, 'incomplete': 0}
            
            if row['status'] == 'completed':
                formatted_stats[category]['completed'] += row['count']
            else:
                formatted_stats[category]['incomplete'] += row['count']
        
        return formatted_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()