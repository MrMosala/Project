# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    JWT_SECRET_KEY = 'your-jwt-secret-key'  
    SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://./BusinessIntelligence_AuthDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
    SQLALCHEMY_BINDS  = { 
        'operational': 'mssql+pyodbc://./BusinessIntelligence_OperationalDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes',
        'audit': 'mssql+pyodbc://./BusinessIntelligence_AuditDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes',
        'archive': 'mssql+pyodbc://./BusinessIntelligence_ArchiveDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False  
    UPLOAD_FOLDER  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'