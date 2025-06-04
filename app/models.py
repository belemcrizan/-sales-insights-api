from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.database import Base
import re
from pydantic import EmailStr
from typing import Optional

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(32), unique=True, nullable=False, comment="Unique stock keeping unit")
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), index=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    sales = relationship("Sale", back_populates="product")
    
    __table_args__ = (
        Index('idx_product_category_name', 'category', 'name'),
        {'comment': 'Product catalog information'},
    )
    
    @validates('sku')
    def validate_sku(self, key, sku):
        if not re.match(r'^[A-Z0-9-]+$', sku):
            raise ValueError("SKU must contain only uppercase letters, numbers and hyphens")
        return sku

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_purchase_at = Column(DateTime, nullable=True)
    
    sales = relationship("Sale", back_populates="customer")
    
    __table_args__ = (
        Index('idx_customer_email_name', 'email', 'name'),
        {'comment': 'Customer information and contact details'},
    )
    
    @validates('email')
    def validate_email(self, key, email):
        try:
            EmailStr.validate(email)
        except ValueError as e:
            raise ValueError("Invalid email format") from e
        return email.lower()

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    sale_date = Column(DateTime, nullable=False, server_default=func.now())
    payment_method = Column(String(20), nullable=True)
    
    product = relationship("Product", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    
    __table_args__ = (
        Index('idx_sale_date_product', 'sale_date', 'product_id'),
        Index('idx_sale_customer', 'customer_id', 'sale_date'),
        {'comment': 'Sales transaction records'},
    )
    
    @validates('quantity')
    def validate_quantity(self, key, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        return quantity
    
    @validates('unit_price', 'total_amount')
    def validate_prices(self, key, price):
        if price <= 0:
            raise ValueError("Price must be positive")
        return round(price, 2)