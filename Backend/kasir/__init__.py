from flask import Blueprint

kasir_bp = Blueprint('kasir', __name__)

from . import routes
