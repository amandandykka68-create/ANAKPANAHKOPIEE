CREATE DATABASE IF NOT EXISTS anak_panah_kopi;
USE anak_panah_kopi;

CREATE TABLE USERS (
    id_user INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    no_hp VARCHAR(15) NOT NULL,
    role ENUM('Customer', 'Kasir', 'Owner') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE MEJA (
    id_meja INT AUTO_INCREMENT PRIMARY KEY,
    nomor_meja VARCHAR(10) UNIQUE NOT NULL,
    qr_code VARCHAR(255),
    status ENUM('Tersedia', 'Terisi') DEFAULT 'Tersedia'
);

CREATE TABLE MENU (
    id_menu INT AUTO_INCREMENT PRIMARY KEY,
    nama_menu VARCHAR(100) NOT NULL,
    deskripsi TEXT,
    harga FLOAT NOT NULL,
    gambar_menu VARCHAR(255),
    status_menu ENUM('Tersedia', 'Habis') DEFAULT 'Tersedia'
);

CREATE TABLE KERANJANG (
    id_keranjang INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL,
    dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_user) REFERENCES USERS(id_user) ON DELETE CASCADE
);

CREATE TABLE DETAIL_KERANJANG (
    id_detail_keranjang INT AUTO_INCREMENT PRIMARY KEY,
    id_keranjang INT NOT NULL,
    id_menu INT NOT NULL,
    jumlah INT NOT NULL,
    catatan VARCHAR(255),
    subtotal FLOAT NOT NULL,
    FOREIGN KEY (id_keranjang) REFERENCES KERANJANG(id_keranjang) ON DELETE CASCADE,
    FOREIGN KEY (id_menu) REFERENCES MENU(id_menu) ON DELETE CASCADE
);

CREATE TABLE TRANSAKSI (
    id_transaksi INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL,
    id_meja INT,
    id_kasir INT,
    tanggal_transaksi DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_harga FLOAT NOT NULL,
    status_pesanan ENUM('Menunggu Pembayaran', 'Diproses', 'Selesai', 'Dibatalkan') DEFAULT 'Menunggu Pembayaran',
    tipe_pesanan ENUM('Online', 'Offline') DEFAULT 'Online',
    FOREIGN KEY (id_user) REFERENCES USERS(id_user) ON DELETE CASCADE,
    FOREIGN KEY (id_meja) REFERENCES MEJA(id_meja) ON DELETE SET NULL,
    FOREIGN KEY (id_kasir) REFERENCES USERS(id_user) ON DELETE SET NULL
);

CREATE TABLE DETAIL_TRANSAKSI (
    id_detail INT AUTO_INCREMENT PRIMARY KEY,
    id_transaksi INT NOT NULL,
    id_menu INT NOT NULL,
    jumlah INT NOT NULL,
    harga_satuan FLOAT NOT NULL,
    subtotal FLOAT NOT NULL,
    catatan VARCHAR(255),
    FOREIGN KEY (id_transaksi) REFERENCES TRANSAKSI(id_transaksi) ON DELETE CASCADE,
    FOREIGN KEY (id_menu) REFERENCES MENU(id_menu) ON DELETE CASCADE
);

CREATE TABLE PEMBAYARAN (
    id_pembayaran INT AUTO_INCREMENT PRIMARY KEY,
    id_transaksi INT NOT NULL,
    metode_bayar ENUM('Cash', 'QRIS', 'Transfer Bank', 'E-Wallet') NOT NULL,
    total_bayar FLOAT NOT NULL,
    status_bayar ENUM('Pending', 'Berhasil', 'Gagal') DEFAULT 'Pending',
    waktu_bayar DATETIME DEFAULT CURRENT_TIMESTAMP,
    reference_number VARCHAR(100),
    FOREIGN KEY (id_transaksi) REFERENCES TRANSAKSI(id_transaksi) ON DELETE CASCADE
);
