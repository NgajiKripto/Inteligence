"""
MemeCoin Intelligence - API Blueprints
"""

from flask import Blueprint

# Token tracking & discovery
token_bp = Blueprint('token', __name__)

# Analysis & simulation
analysis_bp = Blueprint('analysis', __name__)

# Signals & alerts
signal_bp = Blueprint('signal', __name__)

# Import routes
from . import token, analysis, signal
