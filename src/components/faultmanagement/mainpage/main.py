from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sqlite3
import os

app = FastAPI()

selected_database = ""

# Allowing cross-origin requests
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    if file_name == f"{database}.db":
        # For the main database file
        return os.path.join(".", "Databases", "database_sample_data.db")
    else:
        # For alerts.db and faults.db
        os.makedirs(os.path.join(".", "Databases", database), exist_ok=True)
        return os.path.join(".", "Databases", database, file_name)

@app.get("/list_databases")
def list_databases():
    """
    Returns the list of available databases.
    """
    try:
        if os.path.exists(os.path.join(".", "Databases", "database_sample_data.db")):
            return {"databases": ["database_sample_data"]}
        else:
            raise HTTPException(status_code=404, detail="Database not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/columns_from_db")
def get_columns(database: str):
    """
    Returns the list of column names from the KPIs table.
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

        # Extract numeric columns that can be monitored
        monitorable_columns = [
            column[1] for column in columns
            if column[2].upper() in ('REAL', 'INTEGER', 'FLOAT', 'NUMERIC')
        ]

        conn.close()
        return {"columns": monitorable_columns}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching columns: {str(e)}")

@app.get("/alerts")
def get_alerts(database: str):
    """
    Returns a list of alerts for a specific database.
    """
    database_path = get_db_path(database, "alerts.db")
    
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="Alerts database not found")

    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts")
        alerts = cursor.fetchall()
        conn.close()

        alert_list = [
            {
                "id": alert[0],  # Assuming the first column is the alert ID
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

        # Query to get the columns from the 'devices' table
        cursor.execute("PRAGMA table_info(devices);")
        columns = cursor.fetchall()

        if not columns:
            raise HTTPException(status_code=404, detail="Table 'devices' not found in the database")

        # Extracting just the column names
        
        filtered_columns = [
                column[1] for column in columns  # column[1] is the column name
                if column[2].upper() == "REAL" and column[5] == 0  # column[2] is the type, column[5] is PK flag
            ]

        conn.close()
        return {"columns": filtered_columns}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching columns: {str(e)}")
    
class DetectFaultsRequest(BaseModel):
    database: str

@app.post("/detect_faults")
def detect_faults(request: DetectFaultsRequest):
    print(f"Starting fault detection for database: {request.database}")
    database = request.database
    alerts_database_path = get_db_path(database, "alerts.db")
    main_database_path = get_db_path(database, f"{database}.db")
    faults_database_path = get_db_path(database, "faults.db")
    
    print(f"Using paths:\nAlerts DB: {alerts_database_path}\nMain DB: {main_database_path}\nFaults DB: {faults_database_path}")

    try:
        conn_alerts = sqlite3.connect(alerts_database_path)
        cursor_alerts = conn_alerts.cursor()
        cursor_alerts.execute("SELECT * FROM alerts")
        alerts = cursor_alerts.fetchall()
        print(f"Found {len(alerts)} alerts to process")
        conn_alerts.close()

        if not alerts:
            print("No alerts found to process")
            return {"message": "No alerts found to process"}

        conn_main = sqlite3.connect(main_database_path)
        cursor_main = conn_main.cursor()

        # Create faults table if it doesn't exist
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
                user_id BIGINT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check each alert against KPI values
        for alert in alerts:
            alert_id, alert_title, alert_message, field_name, lower_bound, higher_bound = alert
            print(f"\nProcessing alert: {alert_title}")
            print(f"Checking field: {field_name} (bounds: {lower_bound} - {higher_bound})")
            
            try:
                cursor_main.execute(f"SELECT {field_name}, User_ID, Timestamp FROM kpis")
                values = cursor_main.fetchall()
                print(f"Found {len(values)} KPI values to check")
                
                fault_count = 0
                for value, user_id, timestamp in values:
                    if value < lower_bound or value > higher_bound:
                        fault_count += 1
                        cursor_faults.execute("""
                            INSERT INTO faults (alert_id, alert_title, alert_message, field_name, fault_value, user_id, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (alert_id, alert_title, alert_message, field_name, value, user_id, timestamp))
                print(f"Detected {fault_count} faults for this alert")
                
            except sqlite3.OperationalError as e:
                print(f"Error processing field {field_name}: {str(e)}")
                continue

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
    global selected_database
    print(f"Selected Database: {selected_database}")
    if not selected_database:
        raise HTTPException(status_code=400, detail="No database selected")

    faults_database_path = get_db_path(selected_database, "faults.db")

    print(faults_database_path)

    # Ensure faults.db exists
    if not os.path.exists(faults_database_path):
        raise HTTPException(status_code=404, detail="Faults database not found")

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

def setup_latency_alert(database: str):
    database_path = get_db_path(database, "alerts.db")
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Clear existing alerts
    cursor.execute('DELETE FROM alerts')
    
    # Add only the latency alert
    cursor.execute('''
        INSERT INTO alerts (alert_title, alert_message, field_name, lower_bound, higher_bound)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        "High Latency",
        "Latency exceeded 1000ms threshold",
        "Latency",
        0,  # lower bound
        1000  # higher bound
    ))
    
    conn.commit()
    conn.close()

@app.post("/initialize_alerts")
def initialize_alerts(database: str):
    print(f"Initializing alerts for database: {database}")
    alerts_database_path = get_db_path(database, "alerts.db")
    print(f"Using alerts database path: {alerts_database_path}")
    
    try:
        conn = sqlite3.connect(alerts_database_path)
        cursor = conn.cursor()
        
        print("Creating alerts table if it doesn't exist")
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
        
        print("Clearing existing alerts")
        cursor.execute('DELETE FROM alerts')
        
        print("Adding latency alert")
        cursor.execute('''
            INSERT INTO alerts (alert_title, alert_message, field_name, lower_bound, higher_bound)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            "High Latency",
            "Latency exceeded 1000ms threshold",
            "Latency",
            0,
            1000
        ))
        
        conn.commit()
        conn.close()
        print("Alerts initialized successfully")
        return {"message": "Alerts initialized successfully"}
        
    except Exception as e:
        print(f"Error initializing alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error initializing alerts: {str(e)}")
