import streamlit as st
from database.db import db
from database.models import User, AuditLog
from utils.auth import AuthManager, PasswordPolicy, login_required, role_required
from datetime import datetime, timedelta

@login_required
@role_required(["Admin"])
def render_user_management():
    """Render the user management page."""
    st.title("User Management")
    
    # Create tabs for different functions
    tab1, tab2, tab3 = st.tabs(["Add User", "Manage Users", "User Activity"])
    
    with tab1:
        render_add_user_tab()
    
    with tab2:
        render_manage_users_tab()
    
    with tab3:
        render_user_activity_tab()

def render_add_user_tab():
    """Render the add user tab."""
    st.header("Add New User")
    
    with st.form("add_user_form"):
        username = st.text_input("Username*")
        email = st.text_input("Email*")
        password = st.text_input("Password*", type="password")
        confirm_password = st.text_input("Confirm Password*", type="password")
        role = st.selectbox("Role*", ["User", "Sales", "Admin"])
        
        submitted = st.form_submit_button("Add User")
        
        if submitted:
            if not username or not email or not password:
                st.error("All fields marked with * are required.")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            
            # Validate password
            is_valid, error_message = PasswordPolicy.validate_password(password)
            if not is_valid:
                st.error(f"Password validation failed: {error_message}")
                return
            
            try:
                with db.get_session() as session:
                    # Check if username exists
                    if session.query(User).filter(User.username == username).first():
                        st.error("Username already exists.")
                        return
                    
                    # Check if email exists
                    if session.query(User).filter(User.email == email).first():
                        st.error("Email already exists.")
                        return
                    
                    # Create user
                    hashed_password = AuthManager.hash_password(password)
                    user = User(
                        username=username,
                        email=email,
                        password=hashed_password.decode(),
                        role=role,
                        created_at=datetime.utcnow(),
                        last_password_change=datetime.utcnow(),
                        password_history=[hashed_password.decode()],
                        is_active=True
                    )
                    session.add(user)
                    
                    # Log user creation
                    log = AuditLog(
                        user_id=st.session_state.user_id,
                        action="create_user",
                        details={
                            "created_user": username,
                            "role": role,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    session.add(log)
                    session.commit()
                    
                    st.success("User created successfully!")
                    
            except Exception as e:
                st.error(f"Error creating user: {str(e)}")

def render_manage_users_tab():
    """Render the manage users tab."""
    st.header("Manage Users")
    
    with db.get_session() as session:
        users = session.query(User).all()
        
        for user in users:
            with st.expander(f"{user.username} ({user.role})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("User Information:")
                    st.write(f"Email: {user.email}")
                    st.write(f"Role: {user.role}")
                    st.write(f"Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"Last Login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}")
                    st.write(f"Status: {'Active' if user.is_active else 'Inactive'}")
                
                with col2:
                    # User statistics
                    from database.models import BusinessCard, Company
                    cards_count = session.query(BusinessCard).filter(
                        BusinessCard.created_by_id == user.id
                    ).count()
                    companies_count = session.query(Company).filter(
                        Company.created_by_id == user.id
                    ).count()
                    
                    st.write("Activity Statistics:")
                    st.write(f"Business Cards Created: {cards_count}")
                    st.write(f"Companies Created: {companies_count}")
                
                # Actions
                if user.id != st.session_state.user_id:  # Can't modify self
                    col3, col4, col5 = st.columns(3)
                    
                    with col3:
                        new_role = st.selectbox(
                            "Change Role",
                            ["User", "Sales", "Admin"],
                            index=["User", "Sales", "Admin"].index(user.role),
                            key=f"role_{user.id}"
                        )
                        if new_role != user.role:
                            if st.button("Update Role", key=f"update_role_{user.id}"):
                                user.role = new_role
                                session.commit()
                                st.success("Role updated successfully!")
                    
                    with col4:
                        if st.button("Reset Password", key=f"reset_{user.id}"):
                            temp_password = AuthManager.generate_temp_password()
                            hashed_password = AuthManager.hash_password(temp_password)
                            user.password = hashed_password.decode()
                            user.last_password_change = datetime.utcnow()
                            session.commit()
                            st.info(f"Temporary password: {temp_password}")
                    
                    with col5:
                        if st.button(
                            "Deactivate" if user.is_active else "Activate",
                            key=f"toggle_{user.id}"
                        ):
                            user.is_active = not user.is_active
                            session.commit()
                            st.success(
                                f"User {'deactivated' if not user.is_active else 'activated'} successfully!"
                            )

def render_user_activity_tab():
    """Render the user activity tab."""
    st.header("User Activity Logs")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now() - timedelta(days=30)
        )
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    # User filter
    with db.get_session() as session:
        users = session.query(User).all()
        usernames = ["All Users"] + [user.username for user in users]
        selected_user = st.selectbox("Filter by User", usernames)
        
        # Get filtered logs
        query = session.query(AuditLog)
        
        # Apply date filter
        query = query.filter(
            AuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()),
            AuditLog.timestamp <= datetime.combine(end_date, datetime.max.time())
        )
        
        # Apply user filter
        if selected_user != "All Users":
            user = session.query(User).filter(User.username == selected_user).first()
            if user:
                query = query.filter(AuditLog.user_id == user.id)
        
        logs = query.order_by(AuditLog.timestamp.desc()).all()
        
        if logs:
            for log in logs:
                user = session.query(User).get(log.user_id)
                with st.expander(
                    f"{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {user.username if user else 'Unknown'}"
                ):
                    st.write(f"Action: {log.action}")
                    st.write("Details:")
                    st.json(log.details) 