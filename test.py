from app import app, db

def test_db_connection():
    try:
        with app.app_context():
            # Try to create tables
            db.create_all()
            print("Tables created successfully!")
            
            # List all tables
            print("\nCreated tables:")
            for table in db.metadata.tables.keys():
                print(f"- {table}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_db_connection() 