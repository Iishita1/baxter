import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
import certifi
from pymongo import MongoClient, server_api

# Load environment variables from .env file
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "baxter_db")

class Database:
    client: MongoClient = None
    db = None

db_instance = Database()

def connect_to_mongo():
    """Initialize connection to MongoDB Atlas."""
    try:
        # Create a connection with a 5-second timeout so it doesn't hang
        
        db_instance.client = MongoClient(
            MONGODB_URI, 
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(), # Force use of certifi's CA bundle
            server_api=server_api.ServerApi('1') # Pin to stable Server API
        )
        
        # Ping the database to verify connection
        db_instance.client.admin.command('ping')
        
        # Select the database
        db_instance.db = db_instance.client[DATABASE_NAME]
        print(f"✅ Successfully connected to MongoDB Atlas database: {DATABASE_NAME}")
        
        # Optional: Create indexes for faster lookups
        # Users collection will have a unique roll_no
        db_instance.db.users.create_index("roll_no", unique=True)
        
    except ConnectionFailure as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise e

def close_mongo_connection():
    """Close the MongoDB connection."""
    if db_instance.client:
        db_instance.client.close()
        print("🔌 MongoDB connection closed.")

def get_db():
    """Dependency injection for FastAPI routes."""
    if db_instance.db is None:
        connect_to_mongo()
    return db_instance.db