from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

def get_wib_time():
    return datetime.utcnow() + timedelta(hours=7)

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'USERS'
    id_user = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nama = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    no_hp = db.Column(db.String(15), nullable=False)
    role = db.Column(db.Enum('Customer', 'Kasir', 'Owner'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_wib_time)

class Meja(db.Model):
    __tablename__ = 'MEJA'
    id_meja = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nomor_meja = db.Column(db.String(10), unique=True, nullable=False)
    qr_code = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('Tersedia', 'Terisi'), default='Tersedia')

class Menu(db.Model):
    __tablename__ = 'MENU'
    id_menu = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nama_menu = db.Column(db.String(100), nullable=False)
    deskripsi = db.Column(db.Text, nullable=True)
    harga = db.Column(db.Float, nullable=False)
    kategori = db.Column(db.Enum('Makanan', 'Minuman', 'Cemilan'), default='Minuman')
    gambar_menu = db.Column(db.String(255), nullable=True)
    status_menu = db.Column(db.Enum('Tersedia', 'Habis'), default='Tersedia')

class Keranjang(db.Model):
    __tablename__ = 'KERANJANG'
    id_keranjang = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(100), nullable=False) # Changed from id_user
    dibuat_pada = db.Column(db.DateTime, default=get_wib_time)

class DetailKeranjang(db.Model):
    __tablename__ = 'DETAIL_KERANJANG'
    id_detail_keranjang = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_keranjang = db.Column(db.Integer, db.ForeignKey('KERANJANG.id_keranjang'), nullable=False)
    id_menu = db.Column(db.Integer, db.ForeignKey('MENU.id_menu'), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    catatan = db.Column(db.String(255), nullable=True)
    subtotal = db.Column(db.Float, nullable=False)

class Transaksi(db.Model):
    __tablename__ = 'TRANSAKSI'
    id_transaksi = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Customer info (no longer requires id_user)
    nama_pembeli = db.Column(db.String(100), nullable=False)
    email_pembeli = db.Column(db.String(100), nullable=False)
    no_hp_pembeli = db.Column(db.String(20), nullable=False, default='-')
    nomor_meja = db.Column(db.String(50), nullable=False)
    
    id_kasir = db.Column(db.Integer, db.ForeignKey('USERS.id_user'), nullable=True)
    tanggal_transaksi = db.Column(db.DateTime, default=get_wib_time)
    total_harga = db.Column(db.Float, nullable=False)
    status_pesanan = db.Column(db.Enum('Menunggu Pembayaran', 'Diproses', 'Selesai', 'Dibatalkan'), default='Menunggu Pembayaran')
    tipe_pesanan = db.Column(db.Enum('Online', 'Offline'), default='Online', nullable=False)
    
    # Payment info
    metode_bayar = db.Column(db.Enum('Tunai', 'QRIS'), nullable=False)
    kode_pembayaran = db.Column(db.String(10), nullable=True) # for cash
    bukti_pembayaran = db.Column(db.String(255), nullable=True) # for QRIS URL

class DetailTransaksi(db.Model):
    __tablename__ = 'DETAIL_TRANSAKSI'
    id_detail = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_transaksi = db.Column(db.Integer, db.ForeignKey('TRANSAKSI.id_transaksi'), nullable=False)
    id_menu = db.Column(db.Integer, db.ForeignKey('MENU.id_menu'), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    harga_satuan = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    catatan = db.Column(db.String(255), nullable=True)

