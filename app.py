from flask import Flask
from config import Config
from model import db

def create_app():
    # Setup Flask to use Frontend directory for templates and static files
    app = Flask(__name__, 
                template_folder='Frontend', 
                static_folder='Frontend')
                
    app.config.from_object(Config)
    
    # Initialize Database
    db.init_app(app)
    
    # Import Blueprints
    from Backend.utama import utama_bp
    from Backend.authentication import auth_bp
    from Backend.customer import customer_bp
    from Backend.kasir import kasir_bp
    from Backend.owner import owner_bp
    
    # Register Blueprints
    app.register_blueprint(utama_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(kasir_bp, url_prefix='/kasir')
    app.register_blueprint(owner_bp, url_prefix='/owner')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
