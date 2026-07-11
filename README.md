# Anak Panah Kopi (TA_AnakPanahKopi)

Sistem informasi coffee shop berbasis website yang digunakan untuk membantu proses pemesanan menu, transaksi, pembayaran, pengelolaan menu, serta pelaporan penjualan.

## Fitur Utama

- **Role Management:** Customer, Kasir, dan Owner
- **QR Code Menu:** Customer dapat melakukan scan meja
- **Pemesanan & Keranjang:** Pilih menu, atur jumlah, checkout.
- **Pembayaran:** Mendukung berbagai metode pembayaran (kasir).
- **Notifikasi Email:** Pengiriman invoice via Resend API.
- **Dashboard:** Owner dapat melihat grafik penjualan (Chart.js).
- **Manajemen Gambar:** Upload gambar ke Cloudinary.

## Teknologi

- Backend: Python Flask, Flask-SQLAlchemy (TIDB / MySQL)
- Frontend: HTML5, CSS3, Vanilla JS, Bootstrap / Custom CSS
- Integrasi: Cloudinary, Resend, SweetAlert2, qrcode (Python)

## Instalasi

1. Clone repositori ini.
2. Buat *virtual environment*: `python -m venv venv`
3. Aktifkan *virtual environment*: `venv\Scripts\activate` (Windows)
4. Install dependensi: `pip install -r requirements.txt`
5. Salin `.env.example` ke `.env` (atau langsung atur `.env`) dan sesuaikan kredensial.
6. Buat database `anak_panah_kopi` dan import `database/anak_panah_kopi.sql`.
7. Jalankan aplikasi: `python run.py`
