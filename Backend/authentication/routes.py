from flask import render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from model import db, User
from . import auth_bp
import sqlalchemy.exc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # Cari berdasarkan nama (username)
            user = User.query.filter_by(nama=username).first()
            
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id_user
                session['user_name'] = user.nama
                session['user_role'] = user.role
                
                flash(f'Selamat datang, {user.nama}!', 'success')
                
                if user.role == 'Owner':
                    return redirect(url_for('owner.dashboard'))
                elif user.role == 'Kasir':
                    return redirect(url_for('kasir.dashboard'))
                else:
                    return redirect(url_for('customer.dashboard'))
            else:
                flash('Email atau password salah!', 'error')
        except sqlalchemy.exc.OperationalError:
            flash('Gagal terhubung ke database. Periksa konfigurasi .env', 'error')
            
    return render_template('authentication/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form.get('nama')
        email = f"{nama.replace(' ', '').lower()}@anakpanah.local"
        no_hp = request.form.get('no_hp')
        password = request.form.get('password')
        role = request.form.get('role', 'Customer') # Default to Customer
        
        try:
            # Check if email exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email sudah terdaftar!', 'error')
                return redirect(url_for('auth.register'))
                
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(nama=nama, email=email, password=hashed_password, no_hp=no_hp, role=role)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('auth.login'))
        except sqlalchemy.exc.OperationalError:
            flash('Gagal terhubung ke database. Periksa konfigurasi .env', 'error')
            
    return render_template('authentication/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('auth.login'))

