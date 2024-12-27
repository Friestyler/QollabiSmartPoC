from app import app, db

print("Starting database setup...")

try:
    print("Attempting to create database tables...")
    with app.app_context():
        db.create_all()
        print("Tables created successfully!")
        
        # Print all tables that should have been created
        tables = db.metadata.tables.keys()
        print("\nCreated tables:", list(tables))
        
except Exception as e:
    print(f"An error occurred: {str(e)}")

print("Script completed.") 