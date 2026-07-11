from flask import Blueprint

utama_bp = Blueprint('utama', __name__)

from . import routes
