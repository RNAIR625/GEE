from flask import Flask, g, render_template
import os
import uuid
import sqlite3
from datetime import datetime

# Import database helpers
from db_helpers import get_db, close_connection, init_db

# Import route blueprints
from routes.base import base_bp
from routes.classes import classes_bp
from routes.fields import fields_bp
from routes.env_config import env_config_bp
from routes.tables import tables_bp
from routes.rule_groups import rule_groups_bp

app = Flask(__name__)

# Generate a unique APP_RUNTIME_ID when the application starts
APP_RUNTIME_ID = str(uuid.uuid4())
print(f"Application started with runtime ID: {APP_RUNTIME_ID}")

# Register database connection close on app context teardown
@app.teardown_appcontext
def close_db_connection(exception):
    close_connection(exception)

# Register all blueprints
app.register_blueprint(base_bp, url_prefix='/')
app.register_blueprint(classes_bp, url_prefix='/class')
app.register_blueprint(fields_bp, url_prefix='/fields')
app.register_blueprint(env_config_bp, url_prefix='/env_config')
app.register_blueprint(tables_bp, url_prefix='/tables')
app.register_blueprint(rule_groups_bp, url_prefix='/rule_groups')

# Make APP_RUNTIME_ID available to all templates
@app.context_processor
def inject_runtime_id():
    return dict(app_runtime_id=APP_RUNTIME_ID)

# Add remaining routes that haven't been migrated to blueprints yet
@app.route('/function')
def function():
    return render_template('function.html', active_page='function')


@app.route('/stations')
def stations():
    return render_template('stations.html', active_page='stations')

@app.route('/flow_designer')
def flow_designer():
    return render_template('flow_designer.html', active_page='flow_designer')

if __name__ == '__main__':
    # Initialize the app, including database setup
    init_db()
    
    # Log the app runtime ID
    print(f"Starting application with Runtime ID: {APP_RUNTIME_ID}")
    
    # Clean up any old connections left by previous runs with the same app ID
    # This should never happen in practice, but it's a safety measure
    #with app.app_context():
    #    try:
    #        from db_helpers import modify_db
    #        modify_db('DELETE FROM GEE_ACTIVE_CONNECTIONS WHERE APP_RUNTIME_ID = ?', (APP_RUNTIME_ID,))
    #    except Exception as e:
    #        print(f"Error cleaning up old connections: {str(e)}")
    
    # Start the Flask app on a different port
    app.run(debug=True)