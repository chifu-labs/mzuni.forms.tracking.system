from flask import Flask
import os
import sqlite3

def _read_env_file():
    """Read .env file directly, returns dict of key->value."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    values = {}
    if not os.path.exists(env_path):
        return values
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            values[key.strip()] = val.strip()
    return values

def _migrate_db():
    """Safely add any missing columns to the existing database."""
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///mzuzu_dts.db')
    if not db_url.startswith('sqlite:///'):
        return
    db_path = db_url.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'instance', db_path)
    if not os.path.exists(db_path):
        return

    def add_col(cur, table, column, col_type):
        cur.execute(f"PRAGMA table_info({table})")
        if column not in [row[1] for row in cur.fetchall()]:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    for col, typ in [
        ('officer_name',   'VARCHAR(120)'),
        ('officer_email',  'VARCHAR(120)'),
        ('step_name',      'VARCHAR(150)'),
        ('comment',        'TEXT'),
        ('section_data',   'TEXT'),
        ('signature_path', 'VARCHAR(256)'),
        ('ip_address',     'VARCHAR(50)'),
        ('verified_name',  'VARCHAR(120)'),
        ('approved_at',    'DATETIME'),
    ]:
        add_col(cur, 'approvals', col, typ)
    for col, typ in [
        ('officer_name',  'VARCHAR(120)'),
        ('officer_email', 'VARCHAR(120)'),
        ('step_name',     'VARCHAR(150)'),
        ('ip_address',    'VARCHAR(50)'),
        ('rejected_at',   'DATETIME'),
    ]:
        add_col(cur, 'rejections', col, typ)
    # officer_tokens table
    for col, typ in [
        ('identity_confirmed', 'BOOLEAN DEFAULT 0'),
        ('officer_role',       'VARCHAR(120)'),
        ('used_at',            'DATETIME'),
    ]:
        add_col(cur, 'officer_tokens', col, typ)
    # officer_configs table
    for col, typ in [
        ('officer_role', 'VARCHAR(120)'),
        ('updated_at',   'DATETIME'),
        ('updated_by',   'INTEGER'),
    ]:
        add_col(cur, 'officer_configs', col, typ)
    conn.commit()
    conn.close()

def create_app():
    app = Flask(__name__)

    # ── Load .env directly (guaranteed, no dotenv dependency) ────────
    env = _read_env_file()

    # Also try dotenv as secondary
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Helper: env file first, then os.environ, then default
    def cfg(key, default=''):
        return env.get(key) or os.environ.get(key, default)

    # ── Config ────────────────────────────────────────────────────────
    app.config['SECRET_KEY']                  = cfg('SECRET_KEY', 'mzuzu-dts-secret-key-change-me')
    app.config['SQLALCHEMY_DATABASE_URI']     = cfg('DATABASE_URL', 'sqlite:///mzuzu_dts.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER']               = os.path.join(os.path.dirname(__file__), 'static', 'signatures')

    mail_user = cfg('MAIL_USERNAME')
    mail_pass = cfg('MAIL_PASSWORD')
    app.config['MAIL_SERVER']         = 'smtp.gmail.com'
    app.config['MAIL_PORT']           = 587
    app.config['MAIL_USE_TLS']        = True
    app.config['MAIL_USERNAME']       = mail_user
    app.config['MAIL_PASSWORD']       = mail_pass
    app.config['MAIL_DEFAULT_SENDER'] = ('Mzuzu University DTS', mail_user or 'noreply@mzuni.ac.mw')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from extensions import db, login_manager, mail
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view            = 'auth.login'
    login_manager.login_message         = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    with app.app_context():
        from models.models import (Role, Department, User, FormType, WorkflowStep,
                                   FormSubmission, Approval, Rejection, Notification,
                                   AuditLog, OfficerToken, OfficerConfig)
        db.create_all()
        _migrate_db()
        from utils.seed import seed_data
        seed_data()

    # ── Inject unread notification count into every template ────────
    @app.context_processor
    def inject_unread_count():
        from flask_login import current_user
        from models.models import Notification
        count = 0
        if current_user and current_user.is_authenticated:
            count = Notification.query.filter_by(
                recipient_id=current_user.id, is_read=False
            ).count()
        return dict(unread_notification_count=count)

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.forms import forms_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(forms_bp)
    app.register_blueprint(admin_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
