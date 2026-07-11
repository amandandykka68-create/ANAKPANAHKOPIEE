from flask import render_template, request, session, redirect, url_for, flash
from model import db, Transaksi, DetailTransaksi, Menu, User
from Backend.utils import send_invoice_email, send_whatsapp_message
from . import kasir_bp
from datetime import date

def check_kasir():
    if 'user_role' not in session or session['user_role'] != 'Kasir':
        return False
    return True

@kasir_bp.route('/')
def dashboard():
    if not check_kasir(): return redirect(url_for('auth.login'))
    
    # Pesanan Menunggu Pembayaran & Diproses
    transaksi_menunggu = Transaksi.query.filter_by(status_pesanan='Menunggu Pembayaran').all()
    transaksi_diproses = Transaksi.query.filter_by(status_pesanan='Diproses').all()
    
    # Inject details into each transaksi
    for t in transaksi_menunggu:
        t.details = DetailTransaksi.query.filter_by(id_transaksi=t.id_transaksi).all()
        for d in t.details:
            d.menu = Menu.query.get(d.id_menu)
            
    for t in transaksi_diproses:
        t.details = DetailTransaksi.query.filter_by(id_transaksi=t.id_transaksi).all()
        for d in t.details:
            d.menu = Menu.query.get(d.id_menu)
            
    # Calculate stats for today
    today = date.today()
    all_today = Transaksi.query.filter(db.func.date(Transaksi.tanggal_transaksi) == today).all()
    
    total_pesanan_hari_ini = len(all_today)
    total_pendapatan = sum(t.total_harga for t in all_today if t.status_pesanan == 'Selesai')
    menunggu_count = len(transaksi_menunggu)
    rata_rata_servis = "14m 20s" # Mocked
    
    return render_template('kasir/dashboard.html', 
                           menunggu=transaksi_menunggu, 
                           diproses=transaksi_diproses,
                           total_pesanan=total_pesanan_hari_ini,
                           total_pendapatan=total_pendapatan,
                           rata_rata_servis=rata_rata_servis,
                           menunggu_count=menunggu_count)

@kasir_bp.route('/konfirmasi_tunai', methods=['POST'])
def konfirmasi_tunai():
    if not check_kasir(): return redirect(url_for('auth.login'))
    
    kode = request.form.get('kode_pembayaran')
    transaksi = Transaksi.query.filter_by(kode_pembayaran=kode, status_pesanan='Menunggu Pembayaran', metode_bayar='Tunai').first()
    
    if transaksi:
        transaksi.status_pesanan = 'Diproses'
        transaksi.id_kasir = session.get('user_id')
        db.session.commit()
        proses_kirim_nota(transaksi)
        flash('Pembayaran Tunai berhasil dikonfirmasi. Pesanan mulai diproses & Struk WA otomatis terkirim.', 'success')
    else:
        flash('Kode pembayaran tidak valid atau pesanan sudah diproses.', 'error')
        
    return redirect(url_for('kasir.dashboard'))

@kasir_bp.route('/konfirmasi_qris/<int:id_transaksi>')
def konfirmasi_qris(id_transaksi):
    if not check_kasir(): return redirect(url_for('auth.login'))
    
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    if transaksi.status_pesanan == 'Menunggu Pembayaran' and transaksi.metode_bayar == 'QRIS':
        transaksi.status_pesanan = 'Diproses'
        transaksi.id_kasir = session.get('user_id')
        db.session.commit()
        proses_kirim_nota(transaksi)
        flash('Pembayaran QRIS berhasil dikonfirmasi. Pesanan mulai diproses & Struk WA otomatis terkirim.', 'success')
    
    return redirect(url_for('kasir.dashboard'))

@kasir_bp.route('/selesaikan_pesanan/<int:id_transaksi>')
def selesaikan_pesanan(id_transaksi):
    if not check_kasir(): return redirect(url_for('auth.login'))
    
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    if transaksi.status_pesanan == 'Diproses':
        transaksi.status_pesanan = 'Selesai'
        db.session.commit()
        
        # Kirim notifikasi WA jika nomor valid (minimal 10 digit angka)
        if transaksi.no_hp_pembeli and len(transaksi.no_hp_pembeli) >= 10:
            pesan = f"Halo {transaksi.nama_pembeli}!\n\nPesanan Anda (Meja {transaksi.nomor_meja}) di Anak Panah Kopi sudah SIAP SAJI.\nSilakan ambil pesanan Anda di kasir atau tunggu pramusaji kami mengantarkannya.\n\nTerima kasih!"
            send_whatsapp_message(transaksi.no_hp_pembeli, pesan)
            
        flash('Pesanan selesai diproses & siap saji (Notifikasi WA dikirim)!', 'success')
            
    return redirect(url_for('kasir.dashboard'))

@kasir_bp.route('/kelola_menu_cepat')
def kelola_menu_cepat():
    if not check_kasir(): return redirect(url_for('auth.login'))
    menus = Menu.query.all()
    return render_template('kasir/kelola_menu.html', menus=menus)

@kasir_bp.route('/toggle_menu/<int:id_menu>')
def toggle_menu(id_menu):
    if not check_kasir(): return redirect(url_for('auth.login'))
    menu = Menu.query.get_or_404(id_menu)
    menu.status_menu = 'Habis' if menu.status_menu == 'Tersedia' else 'Tersedia'
    db.session.commit()
    flash(f'Status {menu.nama_menu} diubah menjadi {menu.status_menu}', 'success')
    return redirect(url_for('kasir.kelola_menu_cepat'))

def proses_kirim_nota(transaksi):
    if not transaksi.no_hp_pembeli or len(transaksi.no_hp_pembeli) < 10:
        return False
        
    tanggal_str = transaksi.tanggal_transaksi.strftime('%d %B %Y')
    format_id = f"{transaksi.id_transaksi:03d}"
    
    rincian = ""
    details = DetailTransaksi.query.filter_by(id_transaksi=transaksi.id_transaksi).all()
    for d in details:
        menu = Menu.query.get(d.id_menu)
        nama = menu.nama_menu if menu else "Menu Dihapus"
        qty = f"{d.jumlah}x"
        harga = f"Rp{int(d.subtotal):,}".replace(',', '.')
        left = f"{nama} {qty}".ljust(20)
        rincian += f"{left}{harga}\n"
        
    total_rp = f"Rp{int(transaksi.total_harga):,}".replace(',', '.')
    
    pesan = "ANAK PANAH COFFEE\n"
    pesan += "Jl. Diponegoro No. 10, Salatiga\n"
    pesan += "==============================\n\n"
    pesan += "NOTA PEMBELIAN\n\n"
    pesan += f"No. Pesanan : ORD-{format_id}\n"
    pesan += f"Tanggal     : {tanggal_str}\n"
    pesan += f"Nama        : {transaksi.nama_pembeli}\n"
    pesan += f"Meja        : {transaksi.nomor_meja}\n\n"
    pesan += "------------------------------\n"
    pesan += rincian
    pesan += "------------------------------\n\n"
    pesan += f"TOTAL             {total_rp}\n\n"
    pesan += "Pembayaran\n"
    pesan += f"{transaksi.metode_bayar}\n\n"
    pesan += "Terima kasih telah memesan\n"
    pesan += "di Anak Panah Coffee\n\n"
    pesan += "Silakan tunggu pesanan\n"
    pesan += "dipanggil oleh kasir."
    
    return send_whatsapp_message(transaksi.no_hp_pembeli, pesan)

@kasir_bp.route('/kirim_nota_wa/<int:id_transaksi>')
def kirim_nota_wa(id_transaksi):
    if not check_kasir(): return redirect(url_for('auth.login'))
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    
    if proses_kirim_nota(transaksi):
        flash('Nota berhasil dikirim ulang via WhatsApp (Fonnte)!', 'success')
    else:
        flash('Gagal mengirim Nota WA. Cek token Fonnte atau nomor tujuan.', 'error')
        
    return redirect(url_for('kasir.dashboard'))
