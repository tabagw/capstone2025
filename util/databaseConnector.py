"""
Simple script to test MySQL database connection
"""

import mysql.connector
from mysql.connector import Error

def test_mysql_connection():
    """Test connection to MySQL database"""
    
    # UPDATE THESE WITH YOUR DATABASE INFO
    db_config = {
        'host': 'cooking-captain-db.c650cuym2xic.us-east-1.rds.amazonaws.com',        # or your server IP/hostname
        'user': 'admin',    # your MySQL username
        'password': 'CookingCaptain2024!', # your MySQL password
        'database': 'recipe_db'     # your database name
    }
    
    connection = None
    
    try:
        print("🔌 Attempting to connect to MySQL database...")
        print(f"   Host: {db_config['host']}")
        print(f"   User: {db_config['user']}")
        print(f"   Database: {db_config['database']}")
        print()
        
        # Try to connect
        connection = mysql.connector.connect(**db_config)
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print("✅ SUCCESS! Connected to MySQL Server")
            print(f"   MySQL Server version: {db_info}")
            
            # Get cursor and execute a simple query
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print(f"   Current database: {record[0]}")
            
            cursor.close()
            
    except Error as e:
        print("❌ ERROR: Failed to connect to MySQL")
        print(f"   Error message: {e}")
        print()
        print("Common issues:")
        print("  • Check if MySQL is running")
        print("  • Verify username and password are correct")
        print("  • Make sure the database 'recipe_db' exists")
        print("  • Check if host/port are correct")
        
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("\n🔌 Connection closed")

if __name__ == "__main__":
    test_mysql_connection()