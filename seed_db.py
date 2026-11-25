from api.database import connect_to_mongo, get_db, close_mongo_connection
from api.auth import get_password_hash

def seed():
    connect_to_mongo()
    db = get_db()
    
    users = [
        {
            "roll_no": "ADMIN001",
            "name": "System Admin",
            "role": "admin",
            "email": "admin@baxter.edu",
            "hashed_password": get_password_hash("adminpass")
        },
        {
            "roll_no": "PROF001",
            "name": "Dr. Smith",
            "role": "prof",
            "email": "smith@baxter.edu",
            "hashed_password": get_password_hash("profpass")
        },
        {
            "roll_no": "2410992514",
            "name": "John Doe",
            "role": "student",
            "email": "john@baxter.edu",
            "hashed_password": get_password_hash("studentpass")
        }
    ]
    
    for u in users:
        if not db.users.find_one({"roll_no": u["roll_no"]}):
            db.users.insert_one(u)
            print(f"Created {u['role']} user: {u['roll_no']}")
        else:
            print(f"User {u['roll_no']} already exists")
            
    close_mongo_connection()

if __name__ == "__main__":
    seed()