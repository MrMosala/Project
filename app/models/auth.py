from datetime import datetime
import secrets 
from flask_login import UserMixin
from app import db  
import uuid   
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import declared_attr
from sqlalchemy.ext.declarative import declared_attr

class User(db.Model, UserMixin): 
    __tablename__ = 'Users'
    UserID = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    PasswordHash = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    FirstName = db.Column(db.String(50))
    LastName = db.Column(db.String(50))
    IsActive = db.Column(db.Boolean, default=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, nullable=False)
    LastLogin = db.Column(db.DateTime)
    ProfilePicture = db.Column(db.String(255))
    
    def get_id(self):
        return str(self.UserID)

    def to_dict(self):
        return {
            'id': str(self.UserID),
            'email': self.Email,
            'firstName': self.FirstName,
            'lastName': self.LastName,
            'isActive': self.IsActive,
            'createdAt': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'lastLogin': self.LastLogin.isoformat() if self.LastLogin else None,
            'profilePicture': self.ProfilePicture
        }
    
    def set_password(self, password):
        from app import bcrypt 
        self.PasswordHash = bcrypt.generate_password_hash(password).decode('utf-8')
        
class Role(db.Model): 
    __tablename__ = 'Roles'
    RoleID = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    RoleName = db.Column(db.String(50), unique=True, nullable=False) 

    def to_dict(self):
        return {
            'RoleID': str(self.RoleID),
            'RoleName': self.RoleName,
            'Description': self.Description
        }

class UserRole(db.Model): 
    __tablename__ = 'UserRoles'
    UserID = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Users.UserID'), primary_key=True)
    RoleID = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Roles.RoleID'), primary_key=True)

    def to_dict(self):
        return {
            'UserID': str(self.UserID),
            'RoleID': str(self.RoleID)
        }
 

class Subscription(db.Model):
    __tablename__ = 'Subscriptions'
    SubscriptionID = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    UserID = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Users.UserID'), nullable=False)
    PlanName = db.Column(db.String(50), nullable=False)
    Amount = db.Column(db.Float, nullable=False)
    StartDate = db.Column(db.DateTime, nullable=False)
    EndDate = db.Column(db.DateTime, nullable=False)
    Status = db.Column(db.String(20), nullable=False)
    LastPaymentDate = db.Column(db.DateTime, nullable=False)
    PaymentReference = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'subscriptionId': str(self.SubscriptionID),
            'userId': str(self.UserID),
            'planName': self.PlanName,
            'amount': self.Amount,             
            'startDate': self.StartDate.isoformat() if self.StartDate else None,
            'endDate': self.EndDate.isoformat() if self.EndDate else None,
            'status': self.Status,
            'lastPaymentDate': self.LastPaymentDate.isoformat() if self.LastPaymentDate else None,
            'paymentReference': self.PaymentReference
        }
        
class Token(db.Model):
    __tablename__ = 'Tokens'
    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Users.UserID'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    token_type = db.Column(db.String(50), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('tokens', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'token': self.token,
            'token_type': self.token_type,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_token(cls, user_id, token_type, expiration_delta):
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + expiration_delta
        new_token = cls(user_id=user_id, token=token, token_type=token_type, expires_at=expires_at)
        db.session.add(new_token)
        db.session.commit()
        return new_token

    @classmethod
    def get_valid_token(cls, token, token_type):
        return cls.query.filter_by(token=token, token_type=token_type).filter(cls.expires_at > datetime.utcnow()).first()

    def invalidate(self):
        self.expires_at = datetime.utcnow()
        db.session.commit()
