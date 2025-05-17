from flask import Blueprint

from .base import base_bp
from .classes import classes_bp
from .fields import fields_bp
from .functions import functions_bp
from .rules import rules_bp
from .rule_groups import rule_groups_bp
from .tables import tables_bp
from .env_config import env_config_bp

def register_blueprints(app):
    app.register_blueprint(base_bp, url_prefix='/')
    app.register_blueprint(classes_bp, url_prefix='/classes')
    app.register_blueprint(fields_bp, url_prefix='/fields')
    app.register_blueprint(functions_bp, url_prefix='/functions')
    app.register_blueprint(rules_bp, url_prefix='/rules')
    app.register_blueprint(rule_groups_bp, url_prefix='/rule_groups')
    app.register_blueprint(tables_bp, url_prefix='/tables')
    app.register_blueprint(env_config_bp, url_prefix='/env_config')