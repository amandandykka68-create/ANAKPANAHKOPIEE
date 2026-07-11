import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    
    # Session lifetime agar tidak cepat logout
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mencegah error "Lost connection" di TiDB (Serverless sering memutus koneksi idle)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # Cloudinary configuration
    CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')
