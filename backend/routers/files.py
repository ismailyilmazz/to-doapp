from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
import os
import shutil
from datetime import datetime
import database, models

from routers.auth import get_current_user
# --------------------

router = APIRouter(
    prefix="/api/files",
    tags=["Files"]
)

UPLOAD_DIR = "static/uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024 
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".docx", ".xlsx"}
os.makedirs(UPLOAD_DIR, exist_ok=True)

def validate_file(file: UploadFile):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return file_ext

@router.post("/upload/{task_id}", status_code=201)
async def upload_file(
    task_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Task not found")

        file_ext = validate_file(file)

        timestamp = int(datetime.now().timestamp())
        safe_filename = f"{timestamp}_{file.filename}"
        file_location = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        file_size = os.path.getsize(file_location)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_location)
            raise HTTPException(status_code=400, detail="File is too large (Max 10MB)")


        query = """
        INSERT INTO attachments (task_id, original_name, file_path, file_size, uploader_id)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (task_id, file.filename, file_location, file_size, current_user['id']))
        conn.commit()

        return {"info": "File uploaded successfully", "filename": file.filename}

    except Exception as e:
        if 'file_location' in locals() and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/task/{task_id}")
def get_task_files(task_id: int, current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM attachments WHERE task_id = %s"
        cursor.execute(query, (task_id,))
        files = cursor.fetchall()
        return files
    finally:
        cursor.close()
        conn.close()

@router.get("/download/{file_id}")
def download_file(file_id: int, current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT file_path, original_name FROM attachments WHERE id = %s", (file_id,))
        file_record = cursor.fetchone()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found in DB")

        file_path = file_record['file_path']

        if not os.path.exists(file_path):
             raise HTTPException(status_code=404, detail="File not found on server")

        return FileResponse(path=file_path, filename=file_record['original_name'], media_type='application/octet-stream')

    finally:
        cursor.close()
        conn.close()

@router.delete("/{file_id}")
def delete_file(file_id: int, current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM attachments WHERE id = %s", (file_id,))
        file_record = cursor.fetchone()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        if current_user['role'] != 'admin' and file_record['uploader_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")

        if os.path.exists(file_record['file_path']):
            os.remove(file_record['file_path'])

        cursor.execute("DELETE FROM attachments WHERE id = %s", (file_id,))
        conn.commit()

        return {"info": "File deleted successfully"}

    finally:
        cursor.close()
        conn.close()