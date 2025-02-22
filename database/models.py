from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # Admin/Sales/User
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_password_change: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    password_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    business_cards: Mapped[List["BusinessCard"]] = relationship("BusinessCard", back_populates="created_by_user")
    companies: Mapped[List["Company"]] = relationship("Company", back_populates="created_by_user")

class Company(Base):
    __tablename__ = 'companies'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_primary: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_secondary: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    street_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    social_linkedin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    social_twitter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    social_facebook: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qr_code_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    
    # Relationships
    created_by_user: Mapped["User"] = relationship("User", back_populates="companies")
    business_cards: Mapped[List["BusinessCard"]] = relationship("BusinessCard", back_populates="company")

class BusinessCard(Base):
    __tablename__ = 'business_cards'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('companies.id'), nullable=True)
    event_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fax: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    street_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    social_linkedin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    social_twitter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    social_facebook: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store all parsed data
    qr_code_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    
    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="business_cards")
    created_by_user: Mapped["User"] = relationship("User", back_populates="business_cards")

class ExportLog(Base):
    __tablename__ = 'export_logs'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    export_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Excel, CSV, PDF, vCard, JSON
    export_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    items_exported: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Success, Failed, In Progress 