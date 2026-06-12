from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.models import User, Role, Department, FormType, FormSubmission, AuditLog, WorkflowStep
from extensions import db
from functools import wraps
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.role or current_user.role.name != 'System Administrator':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/')
@login_required
@admin_required
def admin_home():
    total_users = User.query.count()
    total_submissions = FormSubmission.query.count()
    pending = FormSubmission.query.filter_by(status='pending').count()
    approved = FormSubmission.query.filter_by(status='approved').count()
    rejected = FormSubmission.query.filter_by(status='rejected').count()
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
    return render_template('admin/home.html',
                           total_users=total_users, total_submissions=total_submissions,
                           pending=pending, approved=approved, rejected=rejected,
                           recent_logs=recent_logs)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.full_name).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {"activated" if user.is_active else "deactivated"} successfully.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    departments = Department.query.all()
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', user.full_name).strip()
        user.email = request.form.get('email', user.email).strip()
        user.post = request.form.get('post', user.post).strip()
        user.grade = request.form.get('grade', user.grade).strip()
        user.role_id = int(request.form.get('role_id', user.role_id))
        dept_id = request.form.get('department_id')
        user.department_id = int(dept_id) if dept_id else None
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/edit_user.html', user=user, roles=roles, departments=departments)

@admin_bp.route('/submissions')
@login_required
@admin_required
def all_submissions():
    status_filter = request.args.get('status', '')
    query = FormSubmission.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    submissions = query.order_by(FormSubmission.submitted_at.desc()).all()
    return render_template('admin/submissions.html', submissions=submissions, status_filter=status_filter)


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(200).all()
    return render_template('admin/audit_logs.html', logs=logs)

# ── Officer Configuration Management ──────────────────────────────

from models.models import OfficerConfig
from utils.officers import OFFICERS, SECTION_MAP_LABELS

@admin_bp.route('/officers')
@login_required
@admin_required
def manage_officers():
    """Show all officer assignments across all forms, editable from the UI."""
    configs = OfficerConfig.query.order_by(
        OfficerConfig.form_template, OfficerConfig.section_key
    ).all()
    # Build a lookup of what's in DB
    db_map = {(c.form_template, c.section_key): c for c in configs}

    # Merge with hardcoded defaults so admin sees every slot
    all_slots = []
    for tname, sections in OFFICERS.items():
        for sec_key, officer in sections.items():
            db_entry = db_map.get((tname, sec_key))
            all_slots.append({
                'form_template': tname,
                'section_key':   sec_key,
                'label':         SECTION_MAP_LABELS.get(tname, {}).get(sec_key, sec_key),
                'db':            db_entry,
                'default_name':  officer['name'],
                'default_email': officer['email'],
                'default_role':  officer.get('role', ''),
            })
    return render_template('admin/officers.html', slots=all_slots)

@admin_bp.route('/officers/save', methods=['POST'])
@login_required
@admin_required
def save_officer():
    form_template = request.form.get('form_template', '').strip()
    section_key   = request.form.get('section_key', '').strip()
    officer_name  = request.form.get('officer_name', '').strip()
    officer_email = request.form.get('officer_email', '').strip()
    officer_role  = request.form.get('officer_role', '').strip()

    if not (form_template and section_key and officer_name and officer_email):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.manage_officers'))

    cfg = OfficerConfig.query.filter_by(
        form_template=form_template, section_key=section_key
    ).first()
    if cfg:
        cfg.officer_name  = officer_name
        cfg.officer_email = officer_email
        cfg.officer_role  = officer_role
        cfg.is_active     = True
        cfg.updated_by    = current_user.id
        cfg.updated_at    = datetime.now()
    else:
        cfg = OfficerConfig(
            form_template=form_template, section_key=section_key,
            officer_name=officer_name, officer_email=officer_email,
            officer_role=officer_role, updated_by=current_user.id
        )
        db.session.add(cfg)

    db.session.add(AuditLog(
        user_id=current_user.id, action='OFFICER_CONFIG_UPDATED',
        details=f'Updated {form_template}/{section_key} → {officer_name} <{officer_email}>',
        ip_address=request.remote_addr
    ))
    db.session.commit()
    flash(f'Officer updated: {officer_name} ({officer_email})', 'success')
    return redirect(url_for('admin.manage_officers'))

@admin_bp.route('/officers/reset', methods=['POST'])
@login_required
@admin_required
def reset_officer():
    """Revert an officer slot back to the hardcoded default."""
    form_template = request.form.get('form_template', '').strip()
    section_key   = request.form.get('section_key', '').strip()
    cfg = OfficerConfig.query.filter_by(
        form_template=form_template, section_key=section_key
    ).first()
    if cfg:
        db.session.delete(cfg)
        db.session.add(AuditLog(
            user_id=current_user.id, action='OFFICER_CONFIG_RESET',
            details=f'Reset {form_template}/{section_key} to default',
            ip_address=request.remote_addr
        ))
        db.session.commit()
        flash('Officer reset to default.', 'success')
    return redirect(url_for('admin.manage_officers'))

@admin_bp.route('/clear-recents', methods=['POST'])
@login_required
@admin_required
def clear_recents():
    """Wipe all audit logs, notifications, approvals, rejections, and submissions for a clean slate."""
    from models.models import (AuditLog, Notification, Approval, Rejection,
                               FormSubmission, OfficerToken)
    OfficerToken.query.delete()
    Approval.query.delete()
    Rejection.query.delete()
    Notification.query.delete()
    FormSubmission.query.delete()
    AuditLog.query.delete()
    db.session.commit()
    flash('All submissions, audit logs, and notifications have been cleared. Fresh start!', 'success')
    return redirect(url_for('admin.admin_home'))
