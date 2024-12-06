from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sqlite3
import os
import logging

app = FastAPI()

# Configure CORS once
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response

selected_database = "db2"

# Model for adding a new alert
class Alert(BaseModel):
    alert_title: str
    alert_message: str
    field_name: str
    lower_bound: float
    higher_bound: float

def get_db_path(database: str, file_name: str):
    """
    Helper function to get the full path of the database file.
    """
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_path = os.path.join(project_root, "Databases")
    
    # Debug prints
    print(f"Project root: {project_root}")
    print(f"Base path: {base_path}")
    print(f"Database: {database}")
    print(f"File name: {file_name}")
    
    # Create the Databases directory if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    
    if file_name == f"{database}.db":
        # For the main database file
        full_path = os.path.join(base_path, "database_sample_data.db")
    else:
        # For alerts.db and faults.db - store them in the same directory
        full_path = os.path.join(base_path, file_name)
    
    print(f"Full database path: {full_path}")
    print(f"Path exists: {os.path.exists(full_path)}")
    return full_path

@app.get("/list_databases")
def list_databases():
    """
    Returns the list of available databases.
    """
    return {"databases": ["database_sample_data"]}

@app.get("/columns_from_db")
def get_columns(database: str, table: str):
    """
    Returns the list of column names from the specified table in the database.
    """
    print(f"Getting columns for database: {database}, table: {table}")  # Debug print
    database_path = get_db_path(database, f"{database}.db")
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Query to get the columns from the specified table
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()

        if not columns:
            raise HTTPException(status_code=404, detail=f"Table '{table}' not found in the database")

        # Extract only numeric columns that can be monitored
        monitorable_columns = [
            column[1] for column in columns
            if column[2].upper() in ('REAL', 'INTEGER', 'FLOAT', 'NUMERIC')
        ]
        
        print(f"Found columns: {monitorable_columns}")  # Debug print
        conn.close()
        return {"columns": monitorable_columns}

    except Exception as e:
        print(f"Error in get_columns: {str(e)}")  # Debug print
        raise HTTPException(status_code=500, detail=f"Error fetching columns: {str(e)}")

@app.get("/alerts")
def get_alerts(database: str):
    """
    Returns a list of alerts for a specific database.
    """
    print(f"Getting alerts for database: {database}")
    database_path = get_db_path(database, "alerts.db")
    print(f"Using alerts database path: {database_path}")
    
    if not os.path.exists(database_path):
        print(f"Alerts database not found at: {database_path}")
        raise HTTPException(status_code=404, detail="Alerts database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts")
        alerts = cursor.fetchall()
        print(f"Found {len(alerts)} alerts")
        conn.close()

        alert_list = [
            {
                "id": alert[0],
                "alert_title": alert[1],
                "alert_message": alert[2],
                "field_name": alert[3],
                "lower_bound": alert[4],
                "higher_bound": alert[5],
            }
            for alert in alerts
        ]

        return {"alerts": alert_list}

    except Exception as e:
        print(f"Error fetching alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")

@app.post("/add_alert")
def add_alert(alert: Alert, database: str):
    """
    Add an alert to the database.
    """
    database_path = get_db_path(database, "alerts.db")
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Alerts database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO alerts (alert_title, alert_message, field_name, lower_bound, higher_bound) VALUES (?, ?, ?, ?, ?)",
            (alert.alert_title, alert.alert_message, alert.field_name, alert.lower_bound, alert.higher_bound),
        )
        conn.commit()
        conn.close()

        return {"message": "Alert added successfully"}

    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"Integrity error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding alert: {str(e)}")


@app.post("/remove_alert")
def remove_alert(alert: dict, database: str):
    """
    Remove an alert from the database.
    """
    alert_id = alert.get("alert_id")
    database_path = get_db_path(database, "alerts.db")
    print(database_path)
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Alerts database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        conn.close()

        return {"message": "Alert removed successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing alert: {str(e)}")

@app.get("/raw_data")
def get_raw_data(database: str, table: str):
    """
    Returns the raw data from a specific table in the selected database.
    """
    database_path = get_db_path(database, f"{database}.db")
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Fetch data from the specified table
        cursor.execute(f"SELECT * FROM {table}")  # Using parameterized query for table name is not possible directly
        raw_data = cursor.fetchall()
        conn.close()

        return {"raw_data": raw_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching raw data: {str(e)}")
@app.get("/columns_from_devices_table")
def get_columns_from_devices(database: str):
    """
    Returns the list of column names from the 'devices' table in the selected database.
    """
    database_path = get_db_path(database, f"{database}.db")
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Query to get the columns from the 'kpis' table
        cursor.execute("PRAGMA table_info(kpis);")
        columns = cursor.fetchall()

        if not columns:
            raise HTTPException(status_code=404, detail="Table 'kpis' not found in the database")

        # Extract only numeric columns that can be monitored
        monitorable_columns = [
            column[1] for column in columns
            if column[1] in [
                "Signal_Strength",
                "Latency",
                "Required_Bandwidth",
                "Allocated_Bandwidth",
                "Resource_Allocation",
                "Usage_Limit_GB"
            ]
        ]

        conn.close()
        return {"columns": monitorable_columns}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching columns: {str(e)}")
    
class DetectFaultsRequest(BaseModel):
    database: str

@app.post("/detect_faults")
def detect_faults(request: DetectFaultsRequest):
    """
    Detects faults based on current alerts and adds them to faults.db if found.
    """
    database = request.database
    alerts_database_path = get_db_path(database, "alerts.db")
    main_database_path = get_db_path(database, f"{database}.db")
    faults_database_path = get_db_path(database, "faults.db")

    global selected_database
    selected_database = database

    # Ensure all required databases exist
    for path in [alerts_database_path, main_database_path]:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Database not found: {path}")

    try:
        # Read alerts from alerts.db
        conn_alerts = sqlite3.connect(alerts_database_path)
        cursor_alerts = conn_alerts.cursor()
        cursor_alerts.execute("SELECT * FROM alerts")
        alerts = cursor_alerts.fetchall()
        conn_alerts.close()

        if not alerts:
            return {"message": "No alerts found to process"}

        # Connect to the main database to scan for faults
        conn_main = sqlite3.connect(main_database_path)
        cursor_main = conn_main.cursor()

        print(faults_database_path)

        # Ensure faults.db exists and has the required table
        if not os.path.exists(faults_database_path):
            conn_faults = sqlite3.connect(faults_database_path)
            cursor_faults = conn_faults.cursor()
            cursor_faults.execute("""
                CREATE TABLE IF NOT EXISTS faults (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER,
                    alert_title TEXT,
                    alert_message TEXT,
                    field_name TEXT,
                    fault_value REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn_faults.commit()
            conn_faults.close()

        conn_faults = sqlite3.connect(faults_database_path)
        cursor_faults = conn_faults.cursor()

        # Loop through alerts and check for faults
        for alert in alerts:
            alert_id, alert_title, alert_message, field_name, lower_bound, higher_bound = alert

            # Check if the field exists in the main database
            try:
                cursor_main.execute(f"SELECT {field_name} FROM kpis")
                values = cursor_main.fetchall()
            except sqlite3.OperationalError:
                continue  # Skip alerts with invalid fields

            # Detect faults
            for (value,) in values:
                if value < lower_bound or value > higher_bound:
                    # Insert the fault into faults.db
                    cursor_faults.execute("""
                        INSERT INTO faults (alert_id, alert_title, alert_message, field_name, fault_value)
                        VALUES (?, ?, ?, ?, ?)
                    """, (alert_id, alert_title, alert_message, field_name, value))

        conn_faults.commit()
        conn_main.close()
        conn_faults.close()

        return {"message": "Fault detection completed successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during fault detection: {str(e)}")

class RemoveNotificationRequest(BaseModel):
    id: int  # ID of the notification to remove

@app.post("/remove_notification")
def remove_notification(request: RemoveNotificationRequest):
    """
    Removes a notification (fault) from the faults.db database.
    """
    global selected_database

    faults_database_path = get_db_path(selected_database, "faults.db")

    # Ensure faults.db exists
    if not os.path.exists(faults_database_path):
        raise HTTPException(status_code=404, detail="Faults database not found")

    try:
        conn = sqlite3.connect(faults_database_path)
        cursor = conn.cursor()

        # Remove the notification by ID
        cursor.execute("DELETE FROM faults WHERE id = ?", (request.id,))
        conn.commit()

        # Check if the deletion was successful
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")

        conn.close()
        return {"message": f"Notification with ID {request.id} removed successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing notification: {str(e)}")

@app.get("/get_notifications")
def get_notifications():
    """
    Returns a list of notifications (faults) from the faults.db database.
    """
    
    
    # print(f"Selected Database: {selected_database}")
    # print(faults_database_path)
    # print(os.path.exists(faults_database_path))
    if not selected_database:
        raise HTTPException(status_code=400, detail="No database selected")

    faults_database_path = get_db_path(selected_database, "faults.db")

    logging.basicConfig(level=logging.INFO)  # Set the logging level

    # Replace print statements with logging
    logging.debug(faults_database_path)
    logging.debug(os.path.exists(faults_database_path))

    # Ensure faults.db exists
    if not os.path.exists(faults_database_path):
        raise HTTPException(status_code=404, detail="Faults database was not found")

    try:
        conn = sqlite3.connect(faults_database_path)
        cursor = conn.cursor()

        # Fetch all notifications from the faults table
        cursor.execute("SELECT * FROM faults")
        faults = cursor.fetchall()
        conn.close()

        # Map the faults to a list of dictionaries
        notifications = [
            {
                "id": fault[0],
                "alert_id": fault[1],
                "alert_title": fault[2],
                "alert_message": fault[3],
                "field_name": fault[4],
                "fault_value": fault[5],
                "timestamp": fault[6],
            }
            for fault in faults
        ]

        return {"notifications": notifications}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notifications: {str(e)}")

@app.get("/tables_from_db")
def get_tables(database: str):
    """
    Returns the list of available tables in the database.
    """
    database_path = get_db_path(database, f"{database}.db")
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Query to get all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Extract table names and print for debugging
        table_list = [table[0] for table in tables]
        print(f"Found tables: {table_list}")  # Debug print
        
        conn.close()
        return {"tables": table_list}

    except Exception as e:
        print(f"Error in get_tables: {str(e)}")  # Debug print
        raise HTTPException(status_code=500, detail=f"Error fetching tables: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Initialize databases on startup"""
    try:
        # Initialize alerts database
        alerts_path = get_db_path("database_sample_data", "alerts.db")
        if not os.path.exists(alerts_path):
            conn = sqlite3.connect(alerts_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_title TEXT NOT NULL,
                    alert_message TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    lower_bound REAL NOT NULL,
                    higher_bound REAL NOT NULL
                )
            ''')
            conn.commit()
            conn.close()
            print(f"Alerts database initialized at {alerts_path}")
        
        # Verify main database exists
        main_db_path = get_db_path("database_sample_data", "database_sample_data.db")
        if not os.path.exists(main_db_path):
            print(f"WARNING: Main database not found at {main_db_path}")
        else:
            print(f"Main database found at {main_db_path}")
            
    except Exception as e:
        print(f"Error during startup initialization: {e}")
