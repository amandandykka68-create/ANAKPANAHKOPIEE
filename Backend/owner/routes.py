from flask import render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash
from model import db, Menu, User, Transaksi, DetailTransaksi
from Backend.utils import upload_image_to_cloudinary
from . import owner_bp
from datetime import datetime, date, timedelta
import calendar

import csv
from io import StringIO
from flask import Response

def check_owner():
    if 'user_role' not in session or session['user_role'] != 'Owner':
        return False
    return True

# ─────────────────────────────────────────────
#  DASHBOARD (REDIRECT)
# ─────────────────────────────────────────────
@owner_bp.route('/')
def dashboard():
    if not check_owner():
        flash('Anda tidak memiliki akses ke halaman ini', 'error')
        return redirect(url_for('auth.login'))
    return redirect(url_for('owner.laporan'))

# ─────────────────────────────────────────────
#  MANAJEMEN MENU
# ─────────────────────────────────────────────
@owner_bp.route('/menu', methods=['GET'])
def manajemen_menu():
    if not check_owner(): return redirect(url_for('auth.login'))
    menus = Menu.query.all()
    return render_template('owner/manajemen_menu.html', menus=menus)

@owner_bp.route('/menu/add', methods=['POST'])
def add_menu():
    if not check_owner(): return redirect(url_for('auth.login'))
    nama_menu   = request.form.get('nama_menu')
    deskripsi   = request.form.get('deskripsi')
    harga       = request.form.get('harga')
    kategori    = request.form.get('kategori', 'Minuman')
    status_menu = request.form.get('status_menu', 'Tersedia')
    gambar      = request.files.get('gambar_menu')
    gambar_url  = ""
    if gambar and gambar.filename != '':
        url = upload_image_to_cloudinary(gambar)
        if url:
            gambar_url = url
    new_menu = Menu(
        nama_menu=nama_menu, deskripsi=deskripsi,
        harga=float(harga), kategori=kategori, gambar_menu=gambar_url, status_menu=status_menu
    )
    db.session.add(new_menu)
    db.session.commit()
    flash('Menu berhasil ditambahkan!', 'success')
    return redirect(url_for('owner.manajemen_menu'))

@owner_bp.route('/menu/edit/<int:id_menu>', methods=['POST'])
def edit_menu(id_menu):
    if not check_owner(): return redirect(url_for('auth.login'))
    menu = Menu.query.get_or_404(id_menu)
    
    menu.nama_menu   = request.form.get('nama_menu')
    menu.deskripsi   = request.form.get('deskripsi')
    menu.harga       = float(request.form.get('harga'))
    menu.kategori    = request.form.get('kategori', 'Minuman')
    menu.status_menu = request.form.get('status_menu')
    
    gambar = request.files.get('gambar_menu')
    if gambar and gambar.filename != '':
        url = upload_image_to_cloudinary(gambar)
        if url:
            menu.gambar_menu = url
            
    db.session.commit()
    flash('Menu berhasil diperbarui!', 'success')
    return redirect(url_for('owner.manajemen_menu'))

@owner_bp.route('/menu/delete/<int:id_menu>', methods=['POST'])
def delete_menu(id_menu):
    if not check_owner(): return redirect(url_for('auth.login'))
    menu = Menu.query.get_or_404(id_menu)
    db.session.delete(menu)
    db.session.commit()
    flash('Menu berhasil dihapus!', 'success')
    return redirect(url_for('owner.manajemen_menu'))

# ─────────────────────────────────────────────
#  KELOLA KASIR
# ─────────────────────────────────────────────
@owner_bp.route('/kasir')
def kelola_kasir():
    if not check_owner(): return redirect(url_for('auth.login'))
    kasirs = User.query.filter_by(role='Kasir').order_by(User.created_at.desc()).all()
    return render_template('owner/kelola_kasir.html', kasirs=kasirs)

@owner_bp.route('/kasir/add', methods=['POST'])
def add_kasir():
    if not check_owner(): return redirect(url_for('auth.login'))
    nama     = request.form.get('nama')
    email    = f"{nama.replace(' ', '').lower()}@anakpanah.local"
    password = request.form.get('password')
    no_hp    = request.form.get('no_hp', '-')

    if User.query.filter_by(email=email).first():
        flash('Email sudah terdaftar!', 'error')
        return redirect(url_for('owner.kelola_kasir'))
    if User.query.filter_by(nama=nama).first():
        flash('Username sudah digunakan!', 'error')
        return redirect(url_for('owner.kelola_kasir'))

    hashed = generate_password_hash(password, method='pbkdf2:sha256')
    new_kasir = User(nama=nama, email=email, password=hashed, no_hp=no_hp, role='Kasir')
    db.session.add(new_kasir)
    db.session.commit()
    flash(f'Akun kasir "{nama}" berhasil dibuat!', 'success')
    return redirect(url_for('owner.kelola_kasir'))

@owner_bp.route('/kasir/delete/<int:id_user>', methods=['POST'])
def delete_kasir(id_user):
    if not check_owner(): return redirect(url_for('auth.login'))
    kasir = User.query.get_or_404(id_user)
    if kasir.role != 'Kasir':
        flash('Aksi tidak diizinkan.', 'error')
        return redirect(url_for('owner.kelola_kasir'))
    db.session.delete(kasir)
    db.session.commit()
    flash(f'Akun kasir "{kasir.nama}" berhasil dihapus!', 'success')
    return redirect(url_for('owner.kelola_kasir'))

@owner_bp.route('/kasir/reset-password/<int:id_user>', methods=['POST'])
def reset_password_kasir(id_user):
    if not check_owner(): return redirect(url_for('auth.login'))
    kasir = User.query.get_or_404(id_user)
    if kasir.role != 'Kasir':
        flash('Aksi tidak diizinkan.', 'error')
        return redirect(url_for('owner.kelola_kasir'))
    new_password = request.form.get('new_password')
    if not new_password or len(new_password) < 6:
        flash('Password minimal 6 karakter!', 'error')
        return redirect(url_for('owner.kelola_kasir'))
    kasir.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    flash(f'Password kasir "{kasir.nama}" berhasil direset!', 'success')
    return redirect(url_for('owner.kelola_kasir'))

# ─────────────────────────────────────────────
#  LAPORAN
# ─────────────────────────────────────────────
@owner_bp.route('/laporan')
def laporan():
    if not check_owner(): return redirect(url_for('auth.login'))

    today = date.today()

    menus = Menu.query.all()
    menu_dict = {m.id_menu: m for m in menus}

    # ── Harian ──
    laporan_tgl_str = request.args.get('laporan_tgl', today.isoformat())
    try:
        laporan_tgl = datetime.strptime(laporan_tgl_str, '%Y-%m-%d').date()
    except ValueError:
        laporan_tgl = today

    tx_harian = Transaksi.query.filter(
        db.func.date(Transaksi.tanggal_transaksi) == laporan_tgl
    ).order_by(Transaksi.tanggal_transaksi.desc()).all()

    pendapatan_harian = sum(t.total_harga for t in tx_harian if t.status_pesanan == 'Selesai')

    # Preload details untuk tabel harian dan breakdown menu
    tx_ids = [t.id_transaksi for t in tx_harian]
    all_details = DetailTransaksi.query.filter(DetailTransaksi.id_transaksi.in_(tx_ids)).all() if tx_ids else []
    
    details_by_tx = {}
    for d in all_details:
        if d.id_transaksi not in details_by_tx:
            details_by_tx[d.id_transaksi] = []
        d._menu = menu_dict.get(d.id_menu)
        details_by_tx[d.id_transaksi].append(d)

    # Breakdown menu harian
    menu_counts_harian = {}
    for t in tx_harian:
        t._details = details_by_tx.get(t.id_transaksi, [])
        for d in t._details:
            nama = d._menu.nama_menu if d._menu else 'Unknown'
            if nama not in menu_counts_harian:
                menu_counts_harian[nama] = {'qty': 0, 'revenue': 0}
            menu_counts_harian[nama]['qty']     += d.jumlah
            menu_counts_harian[nama]['revenue'] += d.subtotal
            
    top_menu_harian = sorted(menu_counts_harian.items(), key=lambda x: x[1]['qty'], reverse=True)[:5]

    # ── Bulanan ──
    laporan_bulan = int(request.args.get('laporan_bulan', today.month))
    laporan_tahun = int(request.args.get('laporan_tahun', today.year))
    _, days_in_month = calendar.monthrange(laporan_tahun, laporan_bulan)
    first_day = date(laporan_tahun, laporan_bulan, 1)
    last_day  = date(laporan_tahun, laporan_bulan, days_in_month)

    tx_bulanan = Transaksi.query.filter(
        db.func.date(Transaksi.tanggal_transaksi) >= first_day,
        db.func.date(Transaksi.tanggal_transaksi) <= last_day
    ).all()

    pendapatan_bulanan = sum(t.total_harga for t in tx_bulanan if t.status_pesanan == 'Selesai')
    total_tx_bulanan   = len(tx_bulanan)

    # Chart bulanan: per hari
    chart_labels_b = []
    chart_data_b   = []
    for day in range(1, days_in_month + 1):
        d = date(laporan_tahun, laporan_bulan, day)
        rev = sum(
            t.total_harga for t in tx_bulanan
            if t.status_pesanan == 'Selesai' and t.tanggal_transaksi.date() == d
        )
        chart_labels_b.append(str(day))
        chart_data_b.append(rev)

    # All-time Monthly Aggregate for Table
    tx_all_selesai = Transaksi.query.filter_by(status_pesanan='Selesai').with_entities(Transaksi.tanggal_transaksi, Transaksi.total_harga).all()
    monthly_aggregates = {}
    for t in tx_all_selesai:
        my = t.tanggal_transaksi.strftime('%m-%Y')
        if my not in monthly_aggregates:
            monthly_aggregates[my] = {'count': 0, 'revenue': 0, 'sort_key': t.tanggal_transaksi.strftime('%Y-%m')}
        monthly_aggregates[my]['count'] += 1
        monthly_aggregates[my]['revenue'] += t.total_harga
    
    laporan_transaksi_bulan = sorted(monthly_aggregates.items(), key=lambda x: x[1]['sort_key'], reverse=True)

    return render_template(
        'owner/laporan.html',
        # Harian
        laporan_tgl=laporan_tgl_str,
        tx_harian=tx_harian,
        pendapatan_harian=pendapatan_harian,
        top_menu_harian=top_menu_harian,
        # Bulanan
        laporan_bulan=laporan_bulan,
        laporan_tahun=laporan_tahun,
        pendapatan_bulanan=pendapatan_bulanan,
        total_tx_bulanan=total_tx_bulanan,
        laporan_transaksi_bulan=laporan_transaksi_bulan
    )

@owner_bp.route('/laporan/export')
def export_laporan():
    if not check_owner(): return redirect(url_for('auth.login'))
    
    tipe = request.args.get('tipe', 'harian')
    si = StringIO()
    cw = csv.writer(si)

    if tipe == 'harian':
        tgl_str = request.args.get('tgl', date.today().isoformat())
        try:
            tgl = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        except ValueError:
            tgl = date.today()
            
        tx_harian = Transaksi.query.filter(
            db.func.date(Transaksi.tanggal_transaksi) == tgl
        ).order_by(Transaksi.tanggal_transaksi.desc()).all()
        
        cw.writerow(['Laporan Harian', tgl_str])
        cw.writerow(['ID Transaksi', 'Waktu', 'Pembeli', 'Total Harga', 'Metode Bayar', 'Status'])
        
        for t in tx_harian:
            cw.writerow([
                f"ORD-{t.id_transaksi}",
                t.tanggal_transaksi.strftime('%H:%M:%S'),
                t.nama_pembeli,
                t.total_harga,
                t.metode_bayar,
                t.status_pesanan
            ])
        filename = f"Laporan_Harian_{tgl_str}.csv"
        
    elif tipe == 'bulanan':
        # All-time Monthly Aggregate for Table
        tx_all_selesai = Transaksi.query.filter_by(status_pesanan='Selesai').all()
        monthly_aggregates = {}
        for t in tx_all_selesai:
            my = t.tanggal_transaksi.strftime('%m-%Y')
            if my not in monthly_aggregates:
                monthly_aggregates[my] = {'count': 0, 'revenue': 0, 'sort_key': t.tanggal_transaksi.strftime('%Y-%m')}
            monthly_aggregates[my]['count'] += 1
            monthly_aggregates[my]['revenue'] += t.total_harga
        
        laporan_transaksi_bulan = sorted(monthly_aggregates.items(), key=lambda x: x[1]['sort_key'], reverse=True)
        
        cw.writerow(['Laporan Transaksi Bulanan'])
        cw.writerow(['Bulan', 'Jumlah Transaksi Selesai', 'Pendapatan'])
        
        for my, info in laporan_transaksi_bulan:
            cw.writerow([
                my,
                info['count'],
                info['revenue']
            ])
        filename = "Laporan_Bulanan.csv"
        
    else:
        return redirect(url_for('owner.laporan'))

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
