import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

if os.getenv("TESTING") == "1" and os.path.exists(".env.test"):
    load_dotenv(".env.test")
else:
    load_dotenv(".env")
# --- Global variable to hold the connection function (defaults to MySQL) ---
# This allows us to override it easily during testing.
_db_connection_function = None

def set_db_connection_function(func):
    """Sets the function used to get a database connection (for testing)."""
    global _db_connection_function
    _db_connection_function = func

def get_db_connection():
    """Returns a database connection, defaulting to MySQL or using the set override."""
    if _db_connection_function:
        # If set by test_api.py, return the mocked SQLite connection
        return _db_connection_function()
    
    # Default MySQL connection logic
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