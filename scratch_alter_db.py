from app import app
from model import db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE TRANSAKSI ADD COLUMN tipe_pesanan ENUM('Online', 'Offline') DEFAULT 'Online' NOT NULL;"))
        db.session.commit()
        print("Successfully added tipe_pesanan to TRANSAKSI")
    except Exception as e:
        print(f"Error: {e}")
