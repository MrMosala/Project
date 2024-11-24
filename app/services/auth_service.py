import hashlib
from operator import and_

from sqlalchemy import Date, cast
from app import db, bcrypt
from app.models.auth import Subscription, Token, User, Role, UserRole
from uuid import uuid4
from datetime import datetime, timedelta
import jwt
from flask import current_app
from app.services.audit_service import log_audit
from logging_config import default_logger as logger
from sqlalchemy.exc import SQLAlchemyError

class AuthenticationError(Exception):
    pass

class UserNotFoundError(Exception):
    pass

class RegistrationError(Exception):
    pass

class UserUpdateError(Exception):
    pass

def authenticate_user(email, password):
    try:
        user = User.query.filter_by(Email=email).first()
        if user and bcrypt.check_password_hash(user.PasswordHash, password):
            user.LastLogin = datetime.utcnow()
            db.session.commit()
            logger.info(f"User authenticated successfully: {email}")
            log_audit('login', 'Users', user.UserID, additional_info={'email': email})
            return user
        logger.warning(f"Failed login attempt for email: {email}")
        raise AuthenticationError("Invalid email or password")
    except SQLAlchemyError as e:
        logger.error(f"Database error during authentication: {str(e)}")
        raise AuthenticationError("An error occurred during authentication")

def get_user_by_id(user_id):
    try:
        user = User.query.get(user_id)
        if user:
            logger.info(f"User retrieved: {user_id}")
            return user
        logger.warning(f"User not found: {user_id}")
        raise UserNotFoundError(f"User with id {user_id} not found")
    except SQLAlchemyError as e:
        logger.error(f"Database error while retrieving user: {str(e)}")
        raise UserNotFoundError("An error occurred while retrieving the user")

def register_user(email, password, first_name, last_name):
    try:
        existing_user = User.query.filter_by(Email=email).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {email}")
            raise RegistrationError("Email already registered")

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            Email=email,
            PasswordHash=hashed_password,
            FirstName=first_name,
            LastName=last_name,
            CreatedAt=datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"New user registered: {email}")
        log_audit('register', 'Users', new_user.UserID, new_values=new_user.to_dict())
        return new_user
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during user registration: {str(e)}")
        raise RegistrationError("An error occurred during user registration")

def update_user(user_id, first_name=None, last_name=None, email=None):
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Attempt to update non-existent user: {user_id}")
            raise UserUpdateError(f"User with id {user_id} not found")

        old_values = user.to_dict()
        if first_name:
            user.FirstName = first_name
        if last_name:
            user.LastName = last_name
        if email:
            user.Email = email
        db.session.commit()
        logger.info(f"User updated: {user_id}")
        log_audit('update', 'Users', user_id, old_values=old_values, new_values=user.to_dict())
        return user
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during user update: {str(e)}")
        raise UserUpdateError("An error occurred while updating the user")
     

class PaymentProcessingError(Exception):
    pass

def process_payfast_notification(payment_data):
    try:
        payment_status = payment_data.get('payment_status')
        amount_gross = float(payment_data.get('amount_gross', 0))
        m_payment_id = payment_data.get('m_payment_id')
        custom_str1 = payment_data.get('custom_str1')  # Plan name
        user_email = payment_data.get('email_address')

        user = User.query.filter_by(Email=user_email).first()
        if not user:
            logger.warning(f"User not found for email: {user_email}")
            raise PaymentProcessingError("User not found")

        if payment_status == 'COMPLETE':
            subscription = Subscription.query.filter_by(UserID=user.UserID).first()
            if not subscription:
                subscription = Subscription(UserID=user.UserID)

            subscription.PlanName = custom_str1
            subscription.Amount = amount_gross
            subscription.StartDate = datetime.utcnow()
            subscription.EndDate = datetime.utcnow() + timedelta(days=30)  # Assuming monthly subscription
            subscription.Status = 'Active'
            subscription.LastPaymentDate = datetime.utcnow()
            subscription.PaymentReference = m_payment_id

            db.session.add(subscription)
            db.session.commit()

            logger.info(f"Subscription updated for user: {user_email}")
            # Log audit for subscription update
            log_audit(
                action='update',
                table_name='Subscriptions',
                record_id=subscription.SubscriptionID,
                old_values=None if not subscription.SubscriptionID else subscription.to_dict(),
                new_values=subscription.to_dict(),
                additional_info={
                    'user_email': user_email,
                    'payment_status': payment_status,
                    'm_payment_id': m_payment_id
                }
            )
            return True
        else:
            logger.warning(f"Payment not completed for user: {user_email}")
            return False

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during payment processing: {str(e)}")
        raise PaymentProcessingError("An error occurred during payment processing")

def verify_payfast_signature(payload, received_signature):
    # Sort the payload alphabetically
    sorted_payload = sorted(payload.items())
    
    # Create the parameter string
    param_string = "&".join([f"{k}={v}" for k, v in sorted_payload])
    
    # Calculate the signature
    calculated_signature = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    
    return calculated_signature == received_signature
 
def get_user_subscription(user_id):
    try:
        current_date = datetime.utcnow()
        subscription = Subscription.query.filter(
            and_(
                and_(
                    Subscription.UserID == user_id,
                    Subscription.Status == 'Active',
                ),
                    and_(cast(Subscription.StartDate, Date)  <= current_date,
                    cast(Subscription.EndDate, Date)    >= current_date
                )
            )
        ).first()
        
        if subscription:
            return subscription
        else:
            # Check if there's an expired subscription that needs status update
            expired_subscription = Subscription.query.filter(
                and_(
                    and_(
                        Subscription.UserID == user_id,
                        Subscription.Status == 'Active',
                    ),
                    cast(Subscription.EndDate, Date)  < current_date
                )
            ).first()
            
            if expired_subscription:
                expired_subscription.Status = 'Expired'
                db.session.commit()
            
            return None
    except Exception as e:
        logger.error(f"Error fetching user subscription: {str(e)}")
        return None
    
def check_email_exists(email):
    """
    Check if an email exists in the database.
    
    Args:
        email (str): The email address to check.
    
    Returns:
        bool: True if the email exists, False otherwise.
    """
    try:
        user = User.query.filter_by(Email=email).first()
        return user is not None
    except Exception as e:
        logger.error(f"Error checking email existence: {str(e)}")
        raise

def save_reset_token(email):
    """
    Save a password reset token for a user.
    
    Args:
        email (str): The user's email address.

    Returns:
        Token: The token object if saved successfully, False otherwise.
    """
    try:
        user = User.query.filter_by(Email=email).first()
        if user:
            # Delete any existing password reset tokens for this user
            Token.query.filter_by(user_id=user.UserID, token_type='password_reset').delete()
            db.session.flush()
            # Create a new password reset token
            token = Token.create_token(user.UserID, 'password_reset', timedelta(hours=1))
            # Log the creation of the password reset token
            log_audit(
                action='create_password_reset_token',
                table_name='Tokens',
                record_id=token.id,
                new_values={
                    'user_id': str(user.UserID),
                    'token_type': 'password_reset',
                    'expires_at': token.expires_at.isoformat()
                },
                additional_info={'email': email}
            )
            
            db.session.commit()
            return token
        return False
    except Exception as e:
        logger.error(f"Error saving reset token: {str(e)}")
        db.session.rollback()
        return False

def reset_password(token, new_password):
    """
    Reset a user's password using a valid token.

    Args:
        token (str): The password reset token.
        new_password (str): The new password to set.

    Returns:
        bool: True if the password was reset successfully, False otherwise.
    """
    try:
        # Retrieve the token from the database
        token_obj = Token.get_valid_token(token, 'password_reset')
        if not token_obj:
            logger.warning("Invalid or expired password reset token")
            return False

        # Get the user associated with the token
        user = User.query.get(token_obj.user_id)
        if not user:
            logger.error(f"User not found for token: {token}")
            return False

        # Update the user's password
        user.set_password(new_password)

        # Invalidate the used token
        token_obj.invalidate()

        # Log the password reset action
        log_audit(
            action='reset_password',
            table_name='Users',
            record_id=user.UserID,
            new_values={'password': 'REDACTED'},
            additional_info={'email': user.Email}
        )

        db.session.commit()
        logger.info(f"Password reset successfully for user: {user.Email}")
        return True
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        db.session.rollback()
        return False