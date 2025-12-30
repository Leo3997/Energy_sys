import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime

class MySQLDatabase:
    def __init__(self, host, user, password, database):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            # 'database': database # Connect without DB first to create it
        }
        self.target_db = database
        self.conn = None
        self.init_db()

    def init_db(self):
        """Initialize DB and Tables"""
        try:
            # 1. Connect to Server
            self.conn = mysql.connector.connect(**self.config)
            cursor = self.conn.cursor()
            
            # 2. Create DB if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.target_db}")
            self.conn.database = self.target_db # Switch to DB
            
            # 3. Create Tables
            # Table: device_events (Unified table for Injection/Change events)
            # fields: id, timestamp, device_ip, device_type, event_type, details_json
            create_table_query = """
            CREATE TABLE IF NOT EXISTS device_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                device_ip VARCHAR(50),
                device_type VARCHAR(50),
                action_type VARCHAR(50), 
                message TEXT,
                details_json JSON
            )
            """
            cursor.execute(create_table_query)
            print(f"✅ MySQL Connected & Tables Ready: {self.target_db}")
            
        except Error as e:
            print(f"❌ MySQL Init Error: {e}")

    def insert_event(self, device_ip, device_type, action_type, message, details=None):
        if not self.conn or not self.conn.is_connected():
            print("⚠️ MySQL disconnect detected. Attempting to reconnect...")
            self.init_db()
            if not self.conn or not self.conn.is_connected():
                print("❌ MySQL Reconnect failed, skipping insert.")
                return

        try:
            cursor = self.conn.cursor()
            sql = """
            INSERT INTO device_events (device_ip, device_type, action_type, message, details_json) 
            VALUES (%s, %s, %s, %s, %s)
            """
            val = (device_ip, device_type, action_type, message, json.dumps(details or {}))
            cursor.execute(sql, val)
            self.conn.commit()
            print(f"💾 [MySQL] Saved event: {action_type}")
        except Error as e:
            print(f"❌ Insert Error: {e}")

    def fetch_events(self, limit=1000):
        """Fetch recent events for export."""
        if not self.conn or not self.conn.is_connected():
            return []
        try:
            cursor = self.conn.cursor(dictionary=True) # Dict cursor for convenience
            cursor.execute(f"SELECT * FROM device_events ORDER BY event_time DESC LIMIT {limit}")
            return cursor.fetchall()
        except Error as e:
            print(f"❌ Fetch Error: {e}")
            return []

# Usage Example:
# db = MySQLDatabase('115.120.248.123', 'root', 'rootpassword', 'energy')
# db.insert_event('127.0.0.1', 'LUBRICATION_BOT', 'INJECT', 'Force protection', {'temp': 56})
