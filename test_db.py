from api.database import connect_to_mongo, get_db, close_mongo_connection

def main():
    print("Testing connection...")
    connect_to_mongo()
    
    db = get_db()
    # Try to insert a dummy document into a test collection
    result = db.test_collection.insert_one({"status": "Connection successful!"})
    print(f"Inserted test document with ID: {result.inserted_id}")
    
    # Read it back
    doc = db.test_collection.find_one({"_id": result.inserted_id})
    print(f"Read back from Atlas: {doc['status']}")
    
    # Clean up
    db.test_collection.delete_one({"_id": result.inserted_id})
    close_mongo_connection()

if __name__ == "__main__":
    main()