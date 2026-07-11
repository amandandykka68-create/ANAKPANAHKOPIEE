from flask import render_template, request, session, redirect, url_for, flash
from model import db, Menu, Keranjang, DetailKeranjang, Transaksi, DetailTransaksi
from Backend.utils import generate_qris_base64, upload_image_to_cloudinary
import uuid
import random
import string
from . import customer_bp

def get_session_id():
    if 'cart_session_id' not in session:
        session['cart_session_id'] = str(uuid.uuid4())
    return session['cart_session_id']

def get_or_create_cart():
    sid = get_session_id()
    keranjang = Keranjang.query.filter_by(session_id=sid).first()
    if not keranjang:
        keranjang = Keranjang(session_id=sid)
        db.session.add(keranjang)
        db.session.commit()
    return keranjang

@customer_bp.route('/')
def landing():
    sid = get_session_id()
    keranjang = Keranjang.query.filter_by(session_id=sid).first()
    cart_count = 0
    if keranjang:
        cart_count = sum(detail.jumlah for detail in DetailKeranjang.query.filter_by(id_keranjang=keranjang.id_keranjang).all())
    return render_template('customer/landing.html', cart_count=cart_count)

@customer_bp.route('/menu')
def menu():
    # Menampilkan semua menu
    menus = Menu.query.all()
    
    sid = get_session_id()
    keranjang = Keranjang.query.filter_by(session_id=sid).first()
    cart_count = 0
    if keranjang:
        cart_count = sum(detail.jumlah for detail in DetailKeranjang.query.filter_by(id_keranjang=keranjang.id_keranjang).all())
            
    return render_template('customer/dashboard.html', menus=menus, cart_count=cart_count)

@customer_bp.route('/cart/add/<int:id_menu>', methods=['POST'])
def add_to_cart(id_menu):
    menu = Menu.query.get_or_404(id_menu)
    if menu.status_menu == 'Habis':
        flash('Maaf, menu sedang habis.', 'error')
        return redirect(url_for('customer.menu'))
        
    keranjang = get_or_create_cart()
    
    detail = DetailKeranjang.query.filter_by(id_keranjang=keranjang.id_keranjang, id_menu=id_menu).first()
    
    if detail:
        detail.jumlah += 1
        detail.subtotal = detail.jumlah * menu.harga
    else:
        detail = DetailKeranjang(id_keranjang=keranjang.id_keranjang, id_menu=id_menu, jumlah=1, subtotal=menu.harga)
        db.session.add(detail)
        
    db.session.commit()
    flash(f'{menu.nama_menu} ditambahkan ke keranjang!', 'success')
    return redirect(url_for('customer.menu'))

@customer_bp.route('/cart/increase/<int:id_detail>', methods=['POST'])
def increase_cart(id_detail):
    detail = DetailKeranjang.query.get_or_404(id_detail)
    menu = Menu.query.get(detail.id_menu)
    detail.jumlah += 1
    detail.subtotal = detail.jumlah * menu.harga
    db.session.commit()
    return redirect(url_for('customer.view_cart'))

@customer_bp.route('/cart/decrease/<int:id_detail>', methods=['POST'])
def decrease_cart(id_detail):
    detail = DetailKeranjang.query.get_or_404(id_detail)
    menu = Menu.query.get(detail.id_menu)
    if detail.jumlah > 1:
        detail.jumlah -= 1
        detail.subtotal = detail.jumlah * menu.harga
    else:
        db.session.delete(detail)
    db.session.commit()
    return redirect(url_for('customer.view_cart'))

@customer_bp.route('/cart', methods=['GET'])
def view_cart():
    sid = get_session_id()
    keranjang = Keranjang.query.filter_by(session_id=sid).first()
    cart_items = []
    total = 0
    
    if keranjang:
        details = DetailKeranjang.query.filter_by(id_keranjang=keranjang.id_keranjang).all()
        for d in details:
            menu = Menu.query.get(d.id_menu)
            cart_items.append({
                'id_detail': d.id_detail_keranjang,
                'menu': menu,
                'jumlah': d.jumlah,
                'subtotal': d.subtotal
            })
            total += d.subtotal
            
    return render_template('customer/cart.html', cart_items=cart_items, total=total)

@customer_bp.route('/checkout', methods=['POST'])
def checkout():
    sid = get_session_id()
    keranjang = Keranjang.query.filter_by(session_id=sid).first()
    if not keranjang:
        flash('Keranjang kosong!', 'error')
        return redirect(url_for('customer.menu'))
        
    details = DetailKeranjang.query.filter_by(id_keranjang=keranjang.id_keranjang).all()
    if not details:
        flash('Keranjang kosong!', 'error')
        return redirect(url_for('customer.menu'))
        
    # Get form data
    nama_pembeli = request.form.get('nama_pembeli')
    no_hp_pembeli = request.form.get('no_hp_pembeli', '-')
    email_pembeli = request.form.get('email_pembeli', f'{no_hp_pembeli}@anakpanah.local')
    nomor_meja = request.form.get('nomor_meja', '').strip()
    metode_bayar = request.form.get('metode_bayar')
    
    if nomor_meja.startswith('0'):
        flash('Nomor meja tidak valid (tidak boleh diawali angka 0).', 'error')
        return redirect(url_for('customer.view_cart'))
        
    total_harga = sum(d.subtotal for d in details)
    
    kode_pembayaran = None
    if metode_bayar == 'Tunai':
        kode_pembayaran = "APK-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Create Transaksi
    transaksi = Transaksi(
        nama_pembeli=nama_pembeli,
        email_pembeli=email_pembeli,
        no_hp_pembeli=no_hp_pembeli,
        nomor_meja=nomor_meja,
        total_harga=total_harga,
        metode_bayar=metode_bayar,
        kode_pembayaran=kode_pembayaran,
        status_pesanan='Menunggu Pembayaran'
    )
    db.session.add(transaksi)
    db.session.flush()
    
    for d in details:
        dt = DetailTransaksi(id_transaksi=transaksi.id_transaksi, id_menu=d.id_menu, jumlah=d.jumlah, harga_satuan=(d.subtotal/d.jumlah), subtotal=d.subtotal)
        db.session.add(dt)
        db.session.delete(d)
        
    db.session.commit()
    
    if metode_bayar == 'QRIS':
        return redirect(url_for('customer.payment_qris', id_transaksi=transaksi.id_transaksi))
    else:
        return redirect(url_for('customer.payment_cash', id_transaksi=transaksi.id_transaksi))

@customer_bp.route('/payment/qris/<int:id_transaksi>')
def payment_qris(id_transaksi):
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    if transaksi.metode_bayar != 'QRIS': return redirect(url_for('customer.menu'))
    
    qris_data = f"QRIS-ANAKPANAH-{transaksi.id_transaksi}-RP{transaksi.total_harga}"
    qr_image = generate_qris_base64(qris_data)
    
    return render_template('customer/payment_qris.html', transaksi=transaksi, qr_image=qr_image)

@customer_bp.route('/payment/cash/<int:id_transaksi>')
def payment_cash(id_transaksi):
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    if transaksi.metode_bayar != 'Tunai': return redirect(url_for('customer.menu'))
    
    return render_template('customer/payment_cash.html', transaksi=transaksi)

@customer_bp.route('/payment/qris/upload/<int:id_transaksi>', methods=['POST'])
def upload_bukti(id_transaksi):
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    
    bukti = request.files.get('bukti_pembayaran')
    if bukti and bukti.filename != '':
        url = upload_image_to_cloudinary(bukti)
        if url:
            transaksi.bukti_pembayaran = url
            # We don't mark as 'Diproses' yet, wait for Kasir
            db.session.commit()
            flash('Bukti pembayaran berhasil diunggah! Silakan tunggu konfirmasi kasir.', 'success')
        else:
            flash('Gagal mengunggah gambar. Pastikan koneksi internet stabil.', 'error')
    else:
        flash('Silakan pilih file bukti pembayaran.', 'error')
        
    return redirect(url_for('customer.payment_qris', id_transaksi=transaksi.id_transaksi))

@customer_bp.route('/struk/<int:id_transaksi>')
def struk(id_transaksi):
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    
    if transaksi.status_pesanan == 'Menunggu Pembayaran':
        flash('Struk belum tersedia. Pembayaran Anda belum dikonfirmasi oleh Kasir.', 'error')
        if transaksi.metode_bayar == 'QRIS':
            return redirect(url_for('customer.payment_qris', id_transaksi=transaksi.id_transaksi))
        else:
            return redirect(url_for('customer.payment_cash', id_transaksi=transaksi.id_transaksi))
    
    details = DetailTransaksi.query.filter_by(id_transaksi=transaksi.id_transaksi).all()
    items = []
    for d in details:
        menu = Menu.query.get(d.id_menu)
        items.append({
            'nama': menu.nama_menu,
            'jumlah': d.jumlah,
            'subtotal': d.subtotal
        })
        
    return render_template('customer/struk.html', transaksi=transaksi, items=items)

@customer_bp.route('/tracking/<int:id_transaksi>')
def tracking(id_transaksi):
    transaksi = Transaksi.query.get_or_404(id_transaksi)
    
    # Get order details
    details = DetailTransaksi.query.filter_by(id_transaksi=transaksi.id_transaksi).all()
    
    items = []
    for d in details:
        menu = Menu.query.get(d.id_menu)
        items.append({
            'nama': menu.nama_menu,
            'gambar': menu.gambar_menu,
            'jumlah': d.jumlah,
            'harga_satuan': d.harga_satuan,
            'subtotal': d.subtotal
        })
        
    return render_template('customer/tracking.html', transaksi=transaksi, items=items)

