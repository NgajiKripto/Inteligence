"""
MemeCoin Intelligence - Flask Application Factory
AI-powered memecoin trading analysis platform
"""

import os
import warnings

warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # JSON encoding: display unicode directly
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Setup logging
    logger = setup_logger('memecoin')
    
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MemeCoin Intelligence Backend Starting...")
        logger.info("=" * 50)
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Request logging middleware
    @app.before_request
    def log_request():
        req_logger = get_logger('memecoin.request')
        req_logger.debug(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def log_response(response):
        req_logger = get_logger('memecoin.request')
        req_logger.debug(f"Response: {response.status_code}")
        return response
    
    # Register blueprints
    from .api import token_bp, analysis_bp, signal_bp
    app.register_blueprint(token_bp, url_prefix='/api/token')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(signal_bp, url_prefix='/api/signal')
    
    # Health check
    @app.route('/health')
    def health():
        return {
            'status': 'ok',
            'service': 'MemeCoin Intelligence',
            'version': '1.0.0'
        }
    
    # Ensure data directories exist
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
    
    if should_log_startup:
        logger.info("MemeCoin Intelligence Backend Ready")
    
    return app
