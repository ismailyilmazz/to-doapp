import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

if os.getenv("TESTING") == "1" and os.path.exists(".env.test"):
    load_dotenv(".env.test")
else:
    load_dotenv(".env")
_db_connection_function = None

def set_db_connection_function(func):
    """Sets the function used to get a database connection (for testing)."""
    global _db_connection_function
    _db_connection_function = func

def get_db_connection():
    """Returns a database connection, defaulting to MySQL or using the set override."""
    if _db_connection_function:

        return _db_connection_function()
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        if conn and conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None
    
def init_db():
    conn = get_db_connection()
    if conn is None:
        print("Veritabanı bağlantısı başarısız, tablolar oluşturulamadı.")
        return
    cursor = conn.cursor()
    
    try:
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role ENUM('user', 'admin') NOT NULL DEFAULT 'user'
        );
        """
        cursor.execute(create_users_table)
        try:
            cursor.execute("SELECT role FROM users LIMIT 1")
            cursor.fetchall()
        except Error:
            print("Tablo var ama 'role' sütunu eksik. Ekleniyor...")
            cursor.execute("ALTER TABLE users ADD COLUMN role ENUM('user', 'admin') NOT NULL DEFAULT 'user'")

        create_tasks_table = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            status VARCHAR(50) DEFAULT 'pending',
            dueDate DATE,
            dueTime TIME,
            user_id INT,
            assigned_to INT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
        );
        """
        cursor.execute(create_tasks_table)

        try:
            cursor.execute("SELECT assigned_to FROM tasks LIMIT 1")
            cursor.fetchall()
        except Error:
             print("Tablo var ama 'assigned_to' sütunu eksik. Ekleniyor...")
             cursor.execute("ALTER TABLE tasks ADD COLUMN assigned_to INT")
             cursor.execute("ALTER TABLE tasks ADD FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL")


        create_attachments_table = """
        CREATE TABLE IF NOT EXISTS attachments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id INT NOT NULL,
            original_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_size INT NOT NULL,
            upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            uploader_id INT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
        cursor.execute(create_attachments_table)

        conn.commit()
        print("Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu.")
        
    except Error as e:
        print(f"Tablo oluşturma hatası: {e}")
    finally:
        cursor.close()
        conn.close()