# app/__init__.py

import os
import uuid
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt 
from flask_migrate import Migrate
from config import DevelopmentConfig
from flask_apscheduler import APScheduler
from logging_config import default_logger as logger

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
login_manager = LoginManager()

from app.models import *

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app) 
    #db.create_all
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    CORS(app)

    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    from app.services.archive_service import archive_old_data
    
    @scheduler.task('cron', id='archive_old_data', hour=13)  # Run daily at 1 pm
    def scheduled_archive():
        with app.app_context():
            try:
                archive_old_data()
                logger.info("Scheduled archiving completed successfully.")
            except Exception as e:
                logger.error(f"Scheduled archiving failed: {str(e)}")
    
    from app.models.auth import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(uuid.UUID(user_id))
    
    from app.routes import main_bp, auth_bp, file_bp, chatbot_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(file_bp, url_prefix='/files')
    app.register_blueprint(chatbot_bp, url_prefix='/chat')
    app.register_blueprint(main_bp)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        # Import models here
        from app.models.auth import User, Role, UserRole
        
    return app 