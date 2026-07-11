from flask import redirect, url_for
from . import utama_bp

@utama_bp.route('/')
def index():
    return redirect(url_for('customer.landing'))
