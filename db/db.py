import psycopg2
from dotenv import load_dotenv
import os

class DataDB:
    def __init__(self):
        # Load environment variables from .env
        load_dotenv()
        
        # Fetch variables
        self.user = os.getenv("user")
        self.password = os.getenv("password")
        self.host = os.getenv("host")
        self.port = os.getenv("port")
        self.dbname = os.getenv("dbname")
        self.connection = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                dbname=self.dbname
            )
            print("Connection successful!")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.connection = None

    def query_single(self, query, params=None):
        if self.connection is None:
            print("Not connected to the database")
            return None
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result

    def query_all(self, query, params=None):
        if self.connection is None:
            print("Not connected to the database")
            return None
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        return result

    def close(self):
        if self.connection is not None:
            self.connection.close()
            print("Connection closed.")

# Example usage
if __name__ == "__main__":
    db = DataDB()
    db.connect()
    
    # Example query
    result = db.query_single("SELECT NOW();")
    print("Current Time:", result)
    
    db.close()
