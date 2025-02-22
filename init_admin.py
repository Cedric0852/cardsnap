import os
import sys
import getpass
from database.db import db
from database.models import User
from utils.auth import PasswordPolicy, AuthManager
from datetime import datetime

def create_admin_user(username: str, email: str, password: str) -> bool:
    """Create the initial admin user."""
    try:
        # Validate password
        is_valid, error_message = PasswordPolicy.validate_password(password)
        if not is_valid:
            print(f"Error: {error_message}")
            return False
        
        # Hash password
        hashed_password = AuthManager.hash_password(password)
        
        # Create admin user
        admin = User(
            username=username,
            email=email,
            password=hashed_password.decode(),
            role="Admin",
            created_at=datetime.utcnow(),
            last_password_change=datetime.utcnow(),
            password_history=[hashed_password.decode()],
            is_active=True
        )
        
        # Add to database
        db.add_item(admin)
        return True
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False

def main():
    """Initialize the database and create the first admin user."""
    try:
        # Reset database
        print("Resetting database...")
        db.reset_db()
        print("Database reset successfully.")
        
        # Check if admin user already exists
        with db.get_session() as session:
            existing_admin = session.query(User).filter(User.role == "Admin").first()
            if existing_admin:
                print("An admin user already exists.")
                return
        
        # Get admin user details
        print("\nCreate initial admin user")
        print("-" * 30)
        
        username = input("Enter admin username: ").strip()
        email = input("Enter admin email: ").strip()
        password = getpass.getpass("Enter admin password: ")
        confirm_password = getpass.getpass("Confirm admin password: ")
        
        # Validate input
        if not username or not email:
            print("Error: Username and email are required.")
            return
            
        if password != confirm_password:
            print("Error: Passwords do not match.")
            return
        
        # Create admin user
        if create_admin_user(username, email, password):
            print("\nAdmin user created successfully!")
            print(f"Username: {username}")
            print("You can now log in to the application.")
        else:
            print("\nFailed to create admin user. Please try again.")
            
    except Exception as e:
        print(f"Error during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 