import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

try:
    # Connect to the database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    print("Successfully connected to the database!")
    
    # Create a cursor
    cur = conn.cursor()
    
    # Execute a simple query
    cur.execute('SELECT 1')
    result = cur.fetchone()
    print(f"Query result: {result[0]}")
    
    # Close the cursor and connection
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error connecting to the database: {e}")
