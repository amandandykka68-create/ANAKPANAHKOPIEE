import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    
    # Database configuration
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'anak_panah_kopi')
    
    # SQLAlchemy configuration
    # Jika menggunakan TiDB Serverless, sangat disarankan menggunakan DATABASE_URL langsung di .env
    # Format TiDB: mysql+pymysql://<user>:<password>@<host>:4000/<dbname>?ssl_verify_cert=true&ssl_verify_identity=true
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback ke MySQL Lokal
        SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mencegah error "Lost connection" di TiDB (Serverless sering memutus koneksi idle)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # Cloudinary configuration
    CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')
    
    # Resend API
    RESEND_API_KEY = os.getenv('RESEND_API_KEY')
