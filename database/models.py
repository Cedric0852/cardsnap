from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # Admin/Sales/User
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    last_password_change = Column(DateTime, default=func.now())
    password_history = Column(JSON)  # Store last 3 password hashes

    # Relationships
    business_cards = relationship("BusinessCard", back_populates="created_by_user")
    companies = relationship("Company", back_populates="created_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_primary = Column(String(20))
    contact_secondary = Column(String(20))
    email = Column(String(120), nullable=False)
    street_address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    website = Column(String(255))
    social_linkedin = Column(String(255))
    social_twitter = Column(String(255))
    social_facebook = Column(String(255))
    qr_code_data = Column(Text)
    logo_path = Column(String(255))
    industry = Column(String(100))
    registration_number = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    created_by_user = relationship("User", back_populates="companies")
    business_cards = relationship("BusinessCard", back_populates="company")

class BusinessCard(Base):
    __tablename__ = 'business_cards'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'))
    event_name = Column(String(100))
    contact_name = Column(String(100))
    position = Column(String(100))
    email = Column(String(120))
    phone = Column(String(20))
    detected_text = Column(Text)
    qr_code_data = Column(Text)
    image_path = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    company = relationship("Company", back_populates="business_cards")
    created_by_user = relationship("User", back_populates="business_cards")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=func.now())
    details = Column(JSON)
    ip_address = Column(String(45))  # IPv6 compatible
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

class ExportLog(Base):
    __tablename__ = 'export_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    export_type = Column(String(20), nullable=False)  # Excel, CSV, PDF, vCard, JSON
    export_date = Column(DateTime, default=func.now())
    items_exported = Column(Integer)
    file_path = Column(String(255))
    status = Column(String(20))  # Success, Failed, In Progress 