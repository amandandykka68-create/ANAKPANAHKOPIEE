// Global Utility Functions for Anak Panah Kopi

document.addEventListener('DOMContentLoaded', () => {
    // Inisialisasi awal
    console.log("Anak Panah Kopi - App Initialized");
});

// Fungsi pembantu untuk menampilkan notifikasi SweetAlert2
window.showAlert = (icon, title, text) => {
    Swal.fire({
        icon: icon,
        title: title,
        text: text,
        confirmButtonColor: '#8C5E35', // Menggunakan warna primary
        cancelButtonColor: '#D9534F',
        fontFamily: "'Outfit', sans-serif",
        customClass: {
            container: 'apk-swal-container',
            popup: 'apk-swal-popup'
        }
    });
};

// Fungsi helper untuk form submission state
window.setLoadingState = (buttonElement, isLoading) => {
    if (isLoading) {
        buttonElement.dataset.originalText = buttonElement.innerHTML;
        buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
        buttonElement.disabled = true;
    } else {
        buttonElement.innerHTML = buttonElement.dataset.originalText;
        buttonElement.disabled = false;
    }
};
