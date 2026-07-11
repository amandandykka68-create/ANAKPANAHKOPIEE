import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import resend
import qrcode
import base64
from io import BytesIO
import cloudinary
import cloudinary.uploader
from flask import render_template

import uuid
from flask import current_app, url_for
from werkzeug.utils import secure_filename

def upload_image_to_cloudinary(file, folder="anak_panah_kopi"):
    """
    Upload file gambar ke Cloudinary dan mengembalikan URL aman.
    Jika gagal atau belum di-setup, akan disimpan secara lokal di folder static/uploads.
    """
    try:
        if os.getenv('CLOUDINARY_URL') and os.getenv('CLOUDINARY_URL') != 'cloudinary://API_KEY:API_SECRET@CLOUD_NAME':
            result = cloudinary.uploader.upload(file, folder=folder)
            return result.get('secure_url')
    except Exception as e:
        print(f"Error upload ke Cloudinary: {e}. Mencoba fallback lokal...")
        
    # Fallback ke penyimpanan lokal
    try:
        upload_dir = os.path.join(current_app.root_path, 'Frontend', 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        # Pindahkan kursor file kembali ke awal jika sudah pernah dibaca (oleh cloudinary)
        file.seek(0)
        
        ext = os.path.splitext(file.filename)[1]
        filename = secure_filename(f"{uuid.uuid4()}{ext}")
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Kembalikan URL lokal (path statis relatif)
        return url_for('static', filename=f'uploads/{filename}')
    except Exception as e:
        print(f"Error upload lokal: {e}")
        return None

def generate_qris_base64(data):
    """
    Membuat QR Code dari string data dan mengembalikannya sebagai Base64 image
    agar bisa langsung dirender di tag <img> HTML.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Error generating QR Code: {e}")
        return None

def send_invoice_email(to_email, transaksi, detail_transaksi):
    """
    Mengirimkan email invoice menggunakan Resend API.
    (Dikembalikan ke Resend karena Gmail SMTP diblokir oleh Google untuk akun pengguna)
    """
    try:
        # Render HTML template dengan Jinja2
        html_content = render_template('email/invoice.html', transaksi=transaksi, detail=detail_transaksi)
        
        api_key = os.getenv('RESEND_API_KEY')
        if not api_key or api_key == 're_your_resend_api_key':
            print("Peringatan: RESEND_API_KEY tidak diatur. Menyimpan invoice secara lokal.")
            # Simpan invoice secara lokal sebagai fallback
            invoice_dir = os.path.join(current_app.root_path, 'static', 'invoices')
            if not os.path.exists(invoice_dir):
                os.makedirs(invoice_dir)
            
            filepath = os.path.join(invoice_dir, f'INV-{transaksi.id_transaksi}.html')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            return True
            
        resend.api_key = api_key
        
        params = {
            "from": "Acme <onboarding@resend.dev>", # Default sender dari Resend untuk testing
            "to": [to_email],
            "subject": f"Invoice Transaksi - Anak Panah Kopi (#{transaksi.id_transaksi})",
            "html": html_content
        }
        
        email_response = resend.Emails.send(params)
        print("Email berhasil dikirim via Resend!", email_response)
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"Error mengirim email via Resend: {error_msg}")
        raise Exception(f"Gagal mengirim email: {error_msg}")

def send_whatsapp_message(target, message):
    """
    Mengirimkan pesan WhatsApp menggunakan Fonnte API.
    Returns: tuple (success: bool, reason: str)
    """
    token = os.getenv('FONNTE_TOKEN')
    if not token:
        print("Peringatan: FONNTE_TOKEN tidak ditemukan di environment")
        return False, "FONNTE_TOKEN tidak ditemukan di Environment Variables Vercel. Tambahkan di Vercel Settings > Environment Variables."
    
    if not target or len(target.strip()) < 5:
        return False, f"Nomor HP pembeli kosong atau tidak valid: '{target}'"
    
    # Bersihkan nomor HP: hapus spasi, strip, dan tanda hubung
    clean_target = target.strip().replace(' ', '').replace('-', '')
    
    # Normalisasi awalan nomor HP Indonesia
    if clean_target.startswith('+62'):
        clean_target = clean_target[3:]
    elif clean_target.startswith('62') and len(clean_target) > 10:
        clean_target = clean_target[2:]
    elif clean_target.startswith('0'):
        clean_target = clean_target[1:]
    
    print(f"[WA DEBUG] Nomor asli: '{target}' -> Nomor bersih: '{clean_target}'")
    print(f"[WA DEBUG] Token (4 char pertama): '{token[:4]}...'")
        
    url = "https://api.fonnte.com/send"
    
    payload = {
        'target': clean_target,
        'message': message,
        'countryCode': '62'
    }
    
    headers = {
        'Authorization': token
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        print(f"[WA DEBUG] Status: {response.status_code}, Response: {result}")
        
        if response.status_code == 200:
            if isinstance(result, dict) and result.get('status') == False:
                reason = result.get('reason', result.get('detail', 'Ditolak oleh Fonnte'))
                print(f"[WA DEBUG] Fonnte menolak: {reason}")
                return False, f"Fonnte menolak: {reason} (Token di server: {token[:4]}...)"
            print("Pesan WhatsApp berhasil dikirim!")
            return True, "Berhasil"
        else:
            detail = result if isinstance(result, str) else str(result)
            print(f"Gagal mengirim WhatsApp. Kode: {response.status_code}, Respon: {detail}")
            return False, f"Fonnte API error (HTTP {response.status_code}): {detail[:200]}"
    except requests.exceptions.Timeout:
        print("Error: Fonnte API timeout")
        return False, "Fonnte API timeout - server tidak merespon dalam 15 detik"
    except Exception as e:
        print(f"Error saat menghubungi Fonnte API: {e}")
        return False, f"Error koneksi ke Fonnte: {str(e)[:200]}"
