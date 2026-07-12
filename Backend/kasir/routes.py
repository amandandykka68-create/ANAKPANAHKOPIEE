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
    
    menus = Menu.query.all()
    menu_dict = {m.id_menu: m for m in menus}
    
    # Pesanan Menunggu Pembayaran & Diproses
    transaksi_menunggu = Transaksi.query.filter_by(status_pesanan='Menunggu Pembayaran').all()
    transaksi_diproses = Transaksi.query.filter_by(status_pesanan='Diproses').all()
    
    # Preload details untuk transaksi aktif
    tx_ids = [t.id_transaksi for t in transaksi_menunggu + transaksi_diproses]
    all_details = DetailTransaksi.query.filter(DetailTransaksi.id_transaksi.in_(tx_ids)).all() if tx_ids else []
    
    details_by_tx = {}
    for d in all_details:
        if d.id_transaksi not in details_by_tx:
            details_by_tx[d.id_transaksi] = []
        d.menu = menu_dict.get(d.id_menu)
        details_by_tx[d.id_transaksi].append(d)
        
    for t in transaksi_menunggu:
        t.details = details_by_tx.get(t.id_transaksi, [])
            
    for t in transaksi_diproses:
        t.details = details_by_tx.get(t.id_transaksi, [])
            
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
        wa_ok, wa_reason = proses_kirim_nota(transaksi)
        if wa_ok:
            flash('Pembayaran Tunai berhasil dikonfirmasi. Pesanan mulai diproses & Struk WA otomatis terkirim.', 'success')
        else:
            flash(f'Pembayaran dikonfirmasi. Tapi WA gagal: {wa_reason}', 'warning')
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
        wa_ok, wa_reason = proses_kirim_nota(transaksi)
        if wa_ok:
            flash('Pembayaran QRIS berhasil dikonfirmasi. Pesanan mulai diproses & Struk WA otomatis terkirim.', 'success')
        else:
            flash(f'Pembayaran dikonfirmasi. Tapi WA gagal: {wa_reason}', 'warning')
    
    return redirect(url_for('kasir.dashboard'))

@kasir_bp.route('/tolak_qris/<int:id_transaksi>')
def tolak_qris(id_transaksi):
    if not check_kasir(): return redirect(url_for('auth.login'))
    
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    if transaksi.status_pesanan == 'Menunggu Pembayaran' and transaksi.metode_bayar == 'QRIS':
        transaksi.bukti_pembayaran = None
        db.session.commit()
        
        # Notify via WA if number is valid
        if transaksi.no_hp_pembeli and len(transaksi.no_hp_pembeli) >= 10:
            pesan = f"Halo {transaksi.nama_pembeli}!\n\nMohon maaf, bukti pembayaran QRIS Anda untuk pesanan ORD-{transaksi.id_transaksi:03d} kami tolak (misal: buram/tidak sesuai).\nSilakan upload ulang bukti pembayaran yang benar melalui halaman pesanan Anda."
            send_whatsapp_message(transaksi.no_hp_pembeli, pesan)
            
        flash('Bukti pembayaran QRIS berhasil ditolak. Customer harus mengunggah ulang.', 'success')
    
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
            wa_ok, wa_reason = send_whatsapp_message(transaksi.no_hp_pembeli, pesan)
            if wa_ok:
                flash('Pesanan selesai & notifikasi WA terkirim!', 'success')
            else:
                flash(f'Pesanan selesai, tapi notif WA gagal: {wa_reason}', 'warning')
        else:
            flash('Pesanan selesai diproses & siap saji!', 'success')
            
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
    """
    Returns: tuple (success: bool, reason: str)
    """
    if not transaksi.no_hp_pembeli or len(transaksi.no_hp_pembeli) < 10:
        return False, f"Nomor HP pembeli kosong atau terlalu pendek: '{transaksi.no_hp_pembeli}'"
        
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
    
    wa_ok, wa_reason = proses_kirim_nota(transaksi)
    if wa_ok:
        flash('Nota berhasil dikirim ulang via WhatsApp (Fonnte)!', 'success')
    else:
        flash(f'Gagal kirim WA: {wa_reason}', 'error')
        
    return redirect(url_for('kasir.dashboard'))

@kasir_bp.route('/pos')
def pos():
    if not check_kasir(): return redirect(url_for('auth.login'))
    menus = Menu.query.filter_by(status_menu='Tersedia').all()
    # Group menus by category
    makanan = [m for m in menus if m.kategori == 'Makanan']
    minuman = [m for m in menus if m.kategori == 'Minuman']
    cemilan = [m for m in menus if m.kategori == 'Cemilan']
    return render_template('kasir/pos.html', makanan=makanan, minuman=minuman, cemilan=cemilan)

@kasir_bp.route('/pos/buat_pesanan', methods=['POST'])
def pos_buat_pesanan():
    if not check_kasir(): return {"status": "error", "message": "Unauthorized"}, 401
    
    data = request.json
    if not data:
        return {"status": "error", "message": "Data tidak valid"}, 400
        
    nama = data.get('nama_pelanggan')
    meja = data.get('nomor_meja', '0')
    if not meja.strip():
        meja = '0'
    no_hp = data.get('no_hp', '-')
    metode = data.get('metode_bayar', 'Tunai')
    items = data.get('items', [])
    
    if not nama or not items:
        return {"status": "error", "message": "Nama pelanggan atau keranjang tidak boleh kosong"}, 400
        
    try:
        total_harga = sum(item['subtotal'] for item in items)
        
        # Buat transaksi dengan tipe_pesanan='Offline'
        transaksi = Transaksi(
            nama_pembeli=nama,
            email_pembeli='offline@kasir.com', # Placeholder for offline
            no_hp_pembeli=no_hp,
            nomor_meja=meja,
            id_kasir=session.get('user_id'),
            total_harga=total_harga,
            status_pesanan='Diproses',
            metode_bayar=metode,
            tipe_pesanan='Offline'
        )
        db.session.add(transaksi)
        db.session.flush() # Untuk mendapatkan id_transaksi
        
        for item in items:
            dt = DetailTransaksi(
                id_transaksi=transaksi.id_transaksi,
                id_menu=item['id_menu'],
                jumlah=item['jumlah'],
                harga_satuan=item['harga'],
                subtotal=item['subtotal'],
                catatan=item.get('catatan', '')
            )
            db.session.add(dt)
            
        db.session.commit()
        
        # Kirim nota WA jika nomor valid
        if no_hp and len(no_hp) >= 10:
            proses_kirim_nota(transaksi)
            
        return {"status": "success", "message": "Pesanan berhasil dibuat!", "id_transaksi": transaksi.id_transaksi}
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}, 500

