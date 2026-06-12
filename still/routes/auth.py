from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.models import User, Role, Department
from extensions import db
from datetime import datetime, timedelta
import os, secrets, base64, io
from PIL import Image

auth_bp = Blueprint('auth', __name__)

def _send_email(to_email, subject, html):
    """Send email using credentials from Flask app config (loaded from .env)."""
    try:
        from flask import current_app
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        sender   = current_app.config.get("MAIL_USERNAME", "")
        password = current_app.config.get("MAIL_PASSWORD", "")
        if not sender or not password:
            print("  Mail not configured – skipping email.")
            return
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Mzuzu University DTS <{sender}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.ehlo()
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, to_email, msg.as_string())
    except Exception as e:
        print(f"Email failed: {e}")

# ── Routes ──────────────────────────────────────────────────────────

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip()
        password    = request.form.get('password', '')
        remember    = request.form.get('remember') == 'on'

        user = User.query.filter_by(employee_id=employee_id).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember,
                       duration=timedelta(days=7) if remember else None)
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.home'))
        flash('Incorrect Employee ID or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Only Senders register. Role is fixed to Sender automatically."""
    if request.method == 'POST':
        employee_id      = request.form.get('employee_id', '').strip()
        full_name        = request.form.get('full_name', '').strip()
        email            = request.form.get('email', '').strip()
        post             = request.form.get('post', '').strip()
        grade            = request.form.get('grade', '').strip()
        password         = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(employee_id=employee_id).first():
            flash('Employee ID already registered.', 'error')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))

        sender_role = Role.query.filter_by(name='Sender').first()
        if not sender_role:
            flash('System error: Sender role not configured. Contact admin.', 'error')
            return redirect(url_for('auth.register'))

        user = User(
            employee_id=employee_id,
            full_name=full_name,
            email=email,
            post=post,
            grade=grade,
            role_id=sender_role.id,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now sign in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw     = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('auth.change_password'))
        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('auth.change_password'))
        if len(new_pw) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(url_for('auth.change_password'))
        current_user.set_password(new_pw)
        db.session.commit()
        flash('Password updated successfully.', 'success')
        return redirect(url_for('dashboard.profile'))
    return render_template('auth/change_password.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user  = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token        = token
            user.reset_token_expiry = datetime.now() + timedelta(hours=1)
            db.session.commit()
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            _send_email(email, "Mzuzu University DTS – Password Reset", f"""
            <html><body style="font-family:Arial,sans-serif;padding:30px;">
            <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
                        padding:32px;border:1px solid #e0e0e0;">
              <h2 style="color:#7c6fff;">Mzuzu University DTS</h2>
              <p>Hi <strong>{user.full_name}</strong>,</p>
              <p>Click the button below to reset your password. This link expires in 1 hour.</p>
              <a href="{reset_link}" style="display:inline-block;margin-top:16px;
                 padding:12px 24px;background:#7c6fff;color:#fff;border-radius:8px;
                 text-decoration:none;font-weight:600;">Reset Password</a>
              <p style="margin-top:24px;font-size:0.8rem;color:#aaa;">
                If you did not request this, ignore this email.</p>
            </div></body></html>""")
        flash('If that email is registered, a reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or \
       user.reset_token_expiry < datetime.now():
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        new_pw     = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        if new_pw != confirm_pw:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        if len(new_pw) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        user.set_password(new_pw)
        user.reset_token        = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Password reset successfully. Please sign in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/upload-signature', methods=['POST'])
@login_required
def upload_signature():
    sig_data = request.form.get('signature_data')
    if sig_data and sig_data.startswith('data:image/'):
        try:
            from flask import current_app
            img_data = base64.b64decode(sig_data.split(',')[1])
            sig_dir  = current_app.config['UPLOAD_FOLDER']
            filename = f"sig_{current_user.id}.png"
            filepath = os.path.join(sig_dir, filename)
            img = Image.open(io.BytesIO(img_data))
            img.save(filepath, 'PNG')
            current_user.signature_path = f"signatures/{filename}"
            db.session.commit()
            flash('Signature saved successfully.', 'success')
        except Exception as e:
            flash(f'Error saving signature: {str(e)}', 'error')
    else:
        flash('Invalid signature data.', 'error')
    return redirect(url_for('dashboard.profile'))
