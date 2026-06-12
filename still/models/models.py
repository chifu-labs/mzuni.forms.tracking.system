from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid, secrets

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Role(db.Model):
    __tablename__ = 'roles'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20),  unique=True, nullable=False)
    users = db.relationship('User', backref='department', lazy=True)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    employee_id   = db.Column(db.String(20),  unique=True, nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    post          = db.Column(db.String(100))
    grade         = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role_id       = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    signature_path = db.Column(db.String(256))
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    reset_token        = db.Column(db.String(256))
    reset_token_expiry = db.Column(db.DateTime)
    submissions   = db.relationship('FormSubmission', backref='submitter', lazy=True,
                                    foreign_keys='FormSubmission.submitted_by')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FormType(db.Model):
    __tablename__ = 'form_types'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(200), nullable=False)
    ref_number    = db.Column(db.String(50))
    description   = db.Column(db.Text)
    template_name = db.Column(db.String(100), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    submissions   = db.relationship('FormSubmission', backref='form_type', lazy=True)
    workflow_steps = db.relationship('WorkflowStep', backref='form_type', lazy=True,
                                     order_by='WorkflowStep.step_order')

class WorkflowStep(db.Model):
    __tablename__ = 'workflow_steps'
    id            = db.Column(db.Integer, primary_key=True)
    form_type_id  = db.Column(db.Integer, db.ForeignKey('form_types.id'), nullable=False)
    step_order    = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    role_id       = db.Column(db.Integer, db.ForeignKey('roles.id'))
    step_name     = db.Column(db.String(150), nullable=False)
    action_label  = db.Column(db.String(100))
    department    = db.relationship('Department')
    role          = db.relationship('Role')

class FormSubmission(db.Model):
    __tablename__ = 'form_submissions'
    id                   = db.Column(db.Integer, primary_key=True)
    tracking_number      = db.Column(db.String(60), unique=True, nullable=False)
    form_type_id         = db.Column(db.Integer, db.ForeignKey('form_types.id'), nullable=False)
    submitted_by         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_step         = db.Column(db.Integer, default=1)
    current_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    status               = db.Column(db.String(30), default='pending')
    form_data            = db.Column(db.Text)
    submitted_at         = db.Column(db.DateTime, default=datetime.now)
    completed_at         = db.Column(db.DateTime)
    current_department   = db.relationship('Department')
    approvals            = db.relationship('Approval',      backref='submission', lazy=True)
    rejections           = db.relationship('Rejection',     backref='submission', lazy=True)
    notifications        = db.relationship('Notification',  backref='submission', lazy=True)
    officer_tokens       = db.relationship('OfficerToken',  backref='submission', lazy=True)

    @staticmethod
    def generate_tracking_number(form_type_ref):
        uid      = str(uuid.uuid4()).replace('-','').upper()[:8]
        now      = datetime.now()
        safe_ref = form_type_ref.replace('/', '-')
        return f"{safe_ref}-{now.year}-{now.month:02d}-{uid}"


# ── Officer tokens (one-time review links) ─────────────────────────
class OfficerToken(db.Model):
    """A single-use signed URL token that lets a hardcoded officer
    review + approve/reject their step without logging in."""
    __tablename__ = 'officer_tokens'
    id            = db.Column(db.Integer, primary_key=True)
    token         = db.Column(db.String(64), unique=True, nullable=False,
                              default=lambda: secrets.token_urlsafe(48))
    submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    step_order    = db.Column(db.Integer, nullable=False)
    officer_email = db.Column(db.String(120), nullable=False)
    officer_name  = db.Column(db.String(120), nullable=False)
    officer_role  = db.Column(db.String(120))
    used          = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    used_at       = db.Column(db.DateTime)
    # identity confirmation: officer must type their name before signing
    identity_confirmed = db.Column(db.Boolean, default=False)


# ── DB-managed officer configuration (replaces hardcoded officers.py) ─
class OfficerConfig(db.Model):
    """Admin-editable table that maps (form template, section) → officer.
    Falls back to officers.py if no DB record exists."""
    __tablename__ = 'officer_configs'
    id            = db.Column(db.Integer, primary_key=True)
    form_template = db.Column(db.String(100), nullable=False)  # e.g. 'procurement'
    section_key   = db.Column(db.String(20),  nullable=False)  # e.g. 'section_c'
    officer_name  = db.Column(db.String(120), nullable=False)
    officer_email = db.Column(db.String(120), nullable=False)
    officer_role  = db.Column(db.String(120))
    is_active     = db.Column(db.Boolean, default=True)
    updated_at    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by    = db.Column(db.Integer, db.ForeignKey('users.id'))
    updater       = db.relationship('User', foreign_keys=[updated_by])

    __table_args__ = (
        db.UniqueConstraint('form_template', 'section_key', name='uq_officer_config'),
    )


class Approval(db.Model):
    __tablename__ = 'approvals'
    id            = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    approved_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    officer_name  = db.Column(db.String(120))
    officer_email = db.Column(db.String(120))
    step_number   = db.Column(db.Integer, nullable=False)
    step_name     = db.Column(db.String(150))
    comment       = db.Column(db.Text)
    section_data  = db.Column(db.Text)
    signature_path = db.Column(db.String(256))
    # audit trail additions
    ip_address    = db.Column(db.String(50))    # IP that submitted the approval
    verified_name = db.Column(db.String(120))   # name the officer typed to confirm identity
    approved_at   = db.Column(db.DateTime, default=datetime.now)
    officer       = db.relationship('User', foreign_keys=[approved_by])

class Rejection(db.Model):
    __tablename__ = 'rejections'
    id            = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    rejected_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    officer_name  = db.Column(db.String(120))
    officer_email = db.Column(db.String(120))
    step_number   = db.Column(db.Integer, nullable=False)
    step_name     = db.Column(db.String(150))
    reason        = db.Column(db.Text, nullable=False)
    ip_address    = db.Column(db.String(50))
    rejected_at   = db.Column(db.DateTime, default=datetime.now)
    officer       = db.relationship('User', foreign_keys=[rejected_by])

class Notification(db.Model):
    __tablename__ = 'notifications'
    id            = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    recipient_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message       = db.Column(db.Text, nullable=False)
    is_read       = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    recipient     = db.relationship('User', foreign_keys=[recipient_id])

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'))
    action     = db.Column(db.String(200), nullable=False)
    details    = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp  = db.Column(db.DateTime, default=datetime.now)
    user       = db.relationship('User', foreign_keys=[user_id])
