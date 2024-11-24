from datetime import timedelta
from flask import current_app, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_login import login_user
from app.services.auth_service import check_email_exists, get_user_subscription, process_payfast_notification, register_user, authenticate_user, get_user_by_id, reset_password, save_reset_token, update_user, verify_payfast_signature
from app.services.auth_service import AuthenticationError, UserNotFoundError, RegistrationError, UserUpdateError
from . import auth_bp
from logging_config import default_logger as logger

@auth_bp.route('/register', methods=['POST'])
@jwt_required(optional=True)
def register():
    try:
        data = request.get_json()
        if not all(key in data for key in ['email', 'password', 'firstName', 'lastName']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        user = register_user(data['email'], data['password'], data['firstName'], data['lastName'])
        return jsonify(user.to_dict()), 201
    except RegistrationError as e:
        logger.warning(f"Registration failed: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@auth_bp.route('/login', methods=['POST'])
@jwt_required(optional=True)
def login():
    try:
        data = request.get_json()
        if not all(key in data for key in ['email', 'password']):
            return jsonify({'error': 'Missing email or password'}), 400
        
        user = authenticate_user(data['email'], data['password'])
        login_user(user)
        access_token = create_access_token(identity=user.UserID, expires_delta=timedelta(days=1))
        # Fetch subscription details
        subscription = get_user_subscription(user.UserID)
        if subscription:
            subscription_dict = subscription.to_dict()
        else:
            subscription_dict = None;
         
        return jsonify({
            'user': user.to_dict(),
            'access_token': access_token,
            'subscription':subscription_dict
        }), 200
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@auth_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    try:
        user_id = get_jwt_identity()
        user = get_user_by_id(user_id)
        return jsonify(user.to_dict())
    except UserNotFoundError as e:
        logger.warning(f"User not found: {str(e)}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Unexpected error while fetching user: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@auth_bp.route('/user', methods=['PUT'])
@jwt_required()
def update_user_route():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        user = update_user(user_id, data.get('firstName'), data.get('lastName'), data.get('email'))
        return jsonify(user.to_dict())
    except UserUpdateError as e:
        logger.warning(f"User update failed: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error during user update: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@auth_bp.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({'error': 'An unexpected error occurred'}), 500
 
@auth_bp.route('/payfast-notify', methods=['POST'])
def payfast_notify():
    try:
        # PayFast server IP addresses
        VALID_IPS = ['41.74.179.194', '41.74.179.195', '41.74.179.196', '41.74.179.197']

        # Check if we're in development mode
        is_development = True
        
        if is_development:
            logger.info(f"Development mode: Bypassing IP check. Request from {request.remote_addr}")
        else:
            # In production, check if the request is coming from a valid PayFast IP
            if request.remote_addr not in VALID_IPS:
                logger.warning(f"Invalid request IP in production: {request.remote_addr}")
                return jsonify({'error': 'Invalid request source'}), 403

        # Extract payment data
        payment_data = request.form.to_dict()
        
        # Log the received data for debugging
        logger.info(f"Received payment data: {payment_data}")

        # Verify the signature (bypass in development mode)
        signature = payment_data.pop('signature', None)
        if not is_development and not verify_payfast_signature(payment_data, signature):
            logger.warning("Invalid PayFast signature in production mode")
            return jsonify({'error': 'Invalid signature'}), 400
        elif is_development:
            logger.info("Development mode: Bypassing signature verification")

        # Process the payment notification
        success = process_payfast_notification(payment_data)

        if success:
            return jsonify({'message': 'Payment processed successfully'}), 200
        else:
            return jsonify({'message': 'Payment not completed'}), 200

    except Exception as e:
        logger.error(f"Error processing PayFast notification: {str(e)}")
        return jsonify({'error': 'An error occurred processing the payment'}), 500
    
@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        exists = check_email_exists(email)
        return jsonify({'exists': exists}), 200

    except Exception as e:
        logger.error(f"Error checking email: {str(e)}")
        return jsonify({'error': 'An error occurred while checking the email'}), 500
    
@auth_bp.route('/save-reset-token', methods=['POST'])
def save_reset_token_route():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Missing required fields'}), 400

        token = save_reset_token(email)
        
        if token:
            return jsonify({'message': 'Reset token saved successfully', 'token': token.token}), 200
        else:
            return jsonify({'error': 'Failed to save reset token'}), 400

    except Exception as e:
        logger.error(f"Error saving reset token: {str(e)}")
        return jsonify({'error': 'An error occurred while saving the reset token'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password_route():
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('password')

        if not token or not new_password:
            return jsonify({'error': 'Missing required fields'}), 400

        success = reset_password(token, new_password)
        
        if success:
            return jsonify({'message': 'Password reset successfully'}), 200
        else:
            return jsonify({'error': 'Invalid or expired token'}), 400

    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return jsonify({'error': 'An error occurred while resetting the password'}), 500
