from flask import Blueprint, render_template, jsonify, request
import uuid
from datetime import datetime

# Create a Blueprint for basic routes
base_bp = Blueprint('base', __name__)

@base_bp.route('/')
def home():
    return render_template('home.html', active_page='home')

@base_bp.route('/get_app_runtime_id')
def get_app_runtime_id():
    """Return the application runtime ID"""
    app_runtime_id = request.args.get('app_runtime_id')
    if not app_runtime_id:
        # Generate a new runtime ID if none provided
        app_runtime_id = str(uuid.uuid4())
        
    return jsonify({
        'app_runtime_id': app_runtime_id,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
