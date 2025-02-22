import re
import bcrypt
from datetime import datetime, timedelta
import jwt
from typing import Optional, Dict, Any
import streamlit as st
from database.models import User
from database.db import db
import string
import random

# Constants
JWT_SECRET = "your-secret-key"  # In production, use environment variable
JWT_ALGORITHM = "HS256"
PASSWORD_HISTORY_SIZE = 3
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_MINUTES = 15

class PasswordPolicy:
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password against security policy.
        Returns (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
            
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
            
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"
            
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
            
        # Check for consecutive repeated characters
        if re.search(r"(.)\1{2,}", password):
            return False, "Password cannot contain consecutive repeated characters"
            
        return True, ""

class AuthManager:
    @staticmethod
    def hash_password(password: str) -> bytes:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt)
    
    @staticmethod
    def verify_password(password: str, hashed_password: bytes) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode(), hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None
    
    @staticmethod
    def check_password_history(user: User, new_password: str) -> bool:
        """Check if the new password exists in password history."""
        if not user.password_history:
            return True
        
        for old_hash in user.password_history:
            if bcrypt.checkpw(new_password.encode(), old_hash.encode()):
                return False
        return True
    
    @staticmethod
    def update_password_history(user: User, new_password_hash: bytes):
        """Update password history for a user."""
        if not user.password_history:
            user.password_history = []
        
        user.password_history.append(new_password_hash.decode())
        if len(user.password_history) > PASSWORD_HISTORY_SIZE:
            user.password_history.pop(0)
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate a user and handle login attempts."""
        with db.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            
            if not user or not user.is_active:
                return None
            
            # Check if user is temporarily blocked
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                last_attempt = user.last_login or datetime.utcnow()
                if datetime.utcnow() - last_attempt < timedelta(minutes=LOGIN_TIMEOUT_MINUTES):
                    return None
                else:
                    # Reset login attempts after timeout
                    user.failed_login_attempts = 0
            
            if AuthManager.verify_password(password, user.password.encode()):
                # Successful login
                user.failed_login_attempts = 0
                user.last_login = datetime.utcnow()
                session.commit()
                return user
            else:
                # Failed login
                user.failed_login_attempts += 1
                session.commit()
                return None
    
    @staticmethod
    def generate_temp_password(length: int = 12) -> str:
        """Generate a secure temporary password."""
        # Define character sets
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Ensure at least one character from each set
        password = [
            random.choice(uppercase),
            random.choice(lowercase),
            random.choice(digits),
            random.choice(special)
        ]
        
        # Fill the rest with random characters
        all_chars = uppercase + lowercase + digits + special
        for _ in range(length - 4):
            password.append(random.choice(all_chars))
        
        # Shuffle the password
        random.shuffle(password)
        
        return ''.join(password)

def login_required(func):
    """Decorator to require login for specific pages."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get("user_id"):
            st.error("Please log in to access this page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    """Decorator to require specific roles for pages."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get("user_id"):
                st.error("Please log in to access this page")
                st.stop()
            
            user_role = st.session_state.get("user_role")
            if user_role not in allowed_roles:
                st.error("You don't have permission to access this page")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator 