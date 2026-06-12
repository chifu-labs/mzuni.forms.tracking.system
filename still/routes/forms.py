from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort, jsonify)
from flask_login import login_required, current_user
from models.models import (FormType, FormSubmission, WorkflowStep, Approval,
                            Rejection, Notification, User, OfficerToken,
                            OfficerConfig, AuditLog)
from extensions import db
from utils.officers import OFFICERS
from datetime import datetime
import json, smtplib, os, base64, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

forms_bp = Blueprint('forms', __name__)

# ── Section key map: step_order → section key ────────────────────
SECTION_MAP = {
    'travel_subsistence': {1:'section_c',2:'section_d',3:'section_e',4:'section_f',5:'section_g',6:'section_h'},
    'procurement':        {1:'section_c',2:'section_d',3:'section_e',4:'section_f',5:'section_g',6:'section_h',7:'section_i'},
    'fuel_requisition':   {1:'section_b',2:'section_c',3:'section_d',4:'section_e'},
    'transport_booking':  {1:'section_b',2:'section_c',3:'section_d'},
}

# ── Email helper ─────────────────────────────────────────────────
def _get_mail_credentials():
    sender   = current_app.config.get('MAIL_USERNAME', '')
    password = current_app.config.get('MAIL_PASSWORD', '')
    if not sender or not password:
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('MAIL_USERNAME='):
                        sender = line.partition('=')[2].strip()
                    elif line.startswith('MAIL_PASSWORD='):
                        password = line.partition('=')[2].strip()
    return sender, password

def _send_raw(to_email, subject, html):
    try:
        sender, password = _get_mail_credentials()
        if not sender or not password:
            logger.warning("Mail not configured – skipping email.")
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
        logger.info("Email sent to %s", to_email)
    except Exception as e:
        logger.error("Email failed to %s: %s", to_email, e)

# ── Officer lookup (DB first, fallback to officers.py) ────────────
def get_officer(template_name, step_order):
    sec = SECTION_MAP.get(template_name, {}).get(step_order)
    if not sec:
        return None
    # Try DB config first (admin-editable)
    cfg = OfficerConfig.query.filter_by(
        form_template=template_name, section_key=sec, is_active=True
    ).first()
    if cfg:
        return {'name': cfg.officer_name, 'email': cfg.officer_email, 'role': cfg.officer_role or ''}
    # Fall back to hardcoded officers.py
    return OFFICERS.get(template_name, {}).get(sec)

# ── Signature save helper ─────────────────────────────────────────
def save_officer_signature(sig_data, token_str):
    if not sig_data:
        return ''
    if sig_data.startswith('TYPED:'):
        return sig_data
    if sig_data.startswith('data:image/'):
        try:
            img_bytes = base64.b64decode(sig_data.split(',')[1])
            sig_dir   = current_app.config['UPLOAD_FOLDER']
            filename  = f"officer_sig_{token_str[:12]}.png"
            filepath  = os.path.join(sig_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(img_bytes)
            return f"signatures/{filename}"
        except Exception as e:
            logger.error("Signature save error: %s", e)
    return ''

# ── Token creation ────────────────────────────────────────────────
def create_officer_token(submission, step, officer):
    tok = OfficerToken(
        submission_id=submission.id,
        step_order=step.step_order,
        officer_email=officer['email'],
        officer_name=officer['name'],
        officer_role=officer.get('role', ''),
    )
    db.session.add(tok)
    db.session.commit()
    return request.host_url.rstrip('/') + url_for('forms.officer_review', token=tok.token)

# ── Notify next officer ───────────────────────────────────────────
def notify_next_step(submission, step):
    tname   = submission.form_type.template_name
    officer = get_officer(tname, step.step_order)
    if not officer:
        return

    review_url = create_officer_token(submission, step, officer)
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
      <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;
                  padding:32px;border:1px solid #e0e0e0;">
        <h2 style="color:#1a3a5c;margin-bottom:4px;">Mzuzu University</h2>
        <h3 style="color:#333;margin-bottom:20px;">Document Tracking System</h3>
        <p style="color:#555;line-height:1.8;">
          Dear <strong>{officer['name']}</strong>,<br><br>
          A document has been routed to you for review and signature.
        </p>
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
          <tr style="background:#e8f0fe;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Form</td>
            <td style="padding:10px;border:1px solid #ddd;">{submission.form_type.name}</td>
          </tr>
          <tr>
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Tracking No.</td>
            <td style="padding:10px;border:1px solid #ddd;">{submission.tracking_number}</td>
          </tr>
          <tr style="background:#e8f0fe;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Your Action</td>
            <td style="padding:10px;border:1px solid #ddd;">{step.step_name}</td>
          </tr>
        </table>
        <p style="color:#555;">Click the button below to open the form and sign your section.
           <strong>No login required.</strong> This link is unique to you and can only be used once.</p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{review_url}"
             style="background:#1a3a5c;color:#fff;padding:13px 30px;
                    text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">
            Review &amp; Sign Form
          </a>
        </div>
        <p style="color:#888;font-size:13px;border-top:1px solid #eee;padding-top:16px;">
          [SECURITY] <strong>Security reminder:</strong> This link is confidential and intended only for
          {officer['name']}. You will be asked to confirm your identity before signing.
          Do not forward this email.
        </p>
        <p style="font-size:0.75rem;color:#aaa;">
          Automated message from Mzuzu University DTS. Do not reply.
        </p>
      </div>
    </body></html>
    """
    _send_raw(officer['email'],
              f"[Mzuzu University DTS] Action Required – {submission.form_type.name}",
              html)

def notify_sender(submitter, subject, body_html):
    _send_raw(submitter.email, subject, body_html)

def _create_notification(submission, recipient_id, message):
    """Create an in-app notification record for the recipient."""
    try:
        notif = Notification(
            submission_id=submission.id,
            recipient_id=recipient_id,
            message=message,
        )
        db.session.add(notif)
    except Exception as e:
        logger.error("Notification create error: %s", e)


# ── Public officer-review routes (NO login required) ─────────────

@forms_bp.route('/officer/review/<token>', methods=['GET', 'POST'])
def officer_review(token):
    tok = OfficerToken.query.filter_by(token=token).first_or_404()

    if tok.used:
        return render_template('forms/officer_done.html',
                               message="This link has already been used. Your action was recorded.")

    sub = tok.submission
    if sub.status != 'pending':
        return render_template('forms/officer_done.html',
                               message=f"This form is no longer pending (status: {sub.status}).")

    step = WorkflowStep.query.filter_by(
        form_type_id=sub.form_type_id, step_order=tok.step_order
    ).first_or_404()

    if sub.current_step != tok.step_order:
        return render_template('forms/officer_done.html',
                               message="This step has already been actioned. Thank you.")

    form_data = json.loads(sub.form_data) if sub.form_data else {}
    officers  = OFFICERS.get(sub.form_type.template_name, {})

    # ── IDENTITY CONFIRMATION (GET — show confirm screen first) ───
    if request.method == 'GET' and not tok.identity_confirmed:
        return render_template('forms/officer_confirm_identity.html',
                               tok=tok, step=step, sub=sub, token=token)

    # ── IDENTITY POST (confirm name before showing form) ──────────
    if request.method == 'POST' and request.form.get('action') == 'confirm_identity':
        entered = request.form.get('entered_name', '').strip()
        expected = tok.officer_name.strip().lower()
        if entered.lower() != expected:
            return render_template('forms/officer_confirm_identity.html',
                                   tok=tok, step=step, sub=sub, token=token,
                                   error="Name does not match our records. Please type your name exactly as shown.")
        tok.identity_confirmed = True
        db.session.commit()
        return render_template(f'forms/{sub.form_type.template_name}_form.html',
                               form_type=sub.form_type, sub=sub, form_data=form_data,
                               current_step_obj=step, mode='officer',
                               officers=officers, token=token, user=None)

    # ── APPROVAL / REJECTION POST ──────────────────────────────────
    if request.method == 'POST':
        action       = request.form.get('action')
        comment      = request.form.get('comment', '').strip()
        section_data = {k: v for k, v in request.form.items()
                        if k not in ['csrf_token', 'comment', 'action', 'entered_name']}

        form_data.update(section_data)
        sub.form_data = json.dumps(form_data)

        # Save officer signature
        sig_path = ''
        for key, val in list(section_data.items()):
            if key.endswith('_signature') or 'signature' in key:
                sig_path = save_officer_signature(val, tok.token)
                section_data[key] = sig_path

        tok.used    = True
        tok.used_at = datetime.now()

        if action == 'approve':
            approval = Approval(
                submission_id=sub.id,
                officer_name=tok.officer_name,
                officer_email=tok.officer_email,
                step_number=sub.current_step,
                step_name=step.step_name,
                comment=comment,
                section_data=json.dumps(section_data),
                signature_path=sig_path,
                ip_address=request.remote_addr,
                verified_name=tok.officer_name,  # confirmed via identity screen
            )
            db.session.add(approval)
            db.session.add(AuditLog(
                action='OFFICER_APPROVED',
                details=f'{tok.officer_name} approved step {sub.current_step} of {sub.tracking_number} from IP {request.remote_addr}',
                ip_address=request.remote_addr
            ))

            next_step = WorkflowStep.query.filter_by(
                form_type_id=sub.form_type_id, step_order=sub.current_step + 1
            ).first()

            if next_step:
                sub.current_step         += 1
                sub.current_department_id = next_step.department_id
                _create_notification(sub, sub.submitted_by,
                    f"Step {step.step_name} approved by {tok.officer_name}. Form is now at: {next_step.step_name}.")
                db.session.commit()
                notify_next_step(sub, next_step)
            else:
                sub.status       = 'approved'
                sub.completed_at = datetime.now()
                _create_notification(sub, sub.submitted_by,
                    f"Your {sub.form_type.name} (Tracking: {sub.tracking_number}) has been FULLY APPROVED.")
                db.session.commit()
                submitter = User.query.get(sub.submitted_by)
                if submitter:
                    notify_sender(submitter,
                        f"[Mzuzu University DTS] Form Fully Approved – {sub.tracking_number}",
                        f"""<html><body style="font-family:Arial,sans-serif;padding:30px;">
                        <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
                                    padding:32px;border:1px solid #e0e0e0;">
                          <h2 style="color:#1a3a5c;">Mzuzu University DTS</h2>
                          <p>Dear <strong>{submitter.full_name}</strong>,</p>
                          <p style="color:#2e7d32;font-weight:bold;">[APPROVED] Your form has been fully approved.</p>
                          <p><strong>Form:</strong> {sub.form_type.name}<br>
                             <strong>Tracking:</strong> {sub.tracking_number}</p>
                        </div></body></html>""")

            return render_template('forms/officer_done.html',
                                   message="[APPROVED] Your approval has been recorded. Thank you!")

        elif action == 'reject':
            reason = comment
            if not reason:
                return render_template(f'forms/{sub.form_type.template_name}_form.html',
                                       form_type=sub.form_type, sub=sub, form_data=form_data,
                                       current_step_obj=step, mode='officer',
                                       officers=officers, token=token, user=None,
                                       error="Please provide a reason for rejection.")

            db.session.add(Rejection(
                submission_id=sub.id,
                officer_name=tok.officer_name,
                officer_email=tok.officer_email,
                step_number=sub.current_step,
                step_name=step.step_name,
                reason=reason,
                ip_address=request.remote_addr,
            ))
            sub.status       = 'rejected'
            sub.completed_at = datetime.now()
            _create_notification(sub, sub.submitted_by,
                f"Your {sub.form_type.name} (Tracking: {sub.tracking_number}) was REJECTED at {step.step_name} by {tok.officer_name}. Reason: {reason}")
            db.session.add(AuditLog(
                action='OFFICER_REJECTED',
                details=f'{tok.officer_name} rejected step {sub.current_step} of {sub.tracking_number}: {reason}',
                ip_address=request.remote_addr
            ))
            db.session.commit()

            submitter = User.query.get(sub.submitted_by)
            if submitter:
                notify_sender(submitter,
                    f"[Mzuzu University DTS] Form Rejected – {sub.tracking_number}",
                    f"""<html><body style="font-family:Arial,sans-serif;padding:30px;">
                    <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
                                padding:32px;border:1px solid #e0e0e0;">
                      <h2 style="color:#1a3a5c;">Mzuzu University DTS</h2>
                      <p>Dear <strong>{submitter.full_name}</strong>,</p>
                      <p style="color:#c62828;font-weight:bold;">[REJECTED] Your form has been rejected.</p>
                      <p><strong>Form:</strong> {sub.form_type.name}<br>
                         <strong>Tracking:</strong> {sub.tracking_number}<br>
                         <strong>Rejected at:</strong> {step.step_name}<br>
                         <strong>Rejected by:</strong> {tok.officer_name}</p>
                      <p><strong>Reason:</strong><br>
                         <span style="background:#ffebee;padding:10px;display:block;
                                      border-radius:6px;margin-top:6px;">{reason}</span></p>
                    </div></body></html>""")

            return render_template('forms/officer_done.html',
                                   message="Your rejection has been recorded and the sender has been notified.")

    # GET with identity already confirmed — show form directly
    return render_template(f'forms/{sub.form_type.template_name}_form.html',
                           form_type=sub.form_type, sub=sub, form_data=form_data,
                           current_step_obj=step, mode='officer',
                           officers=officers, token=token, user=None)


# ── Resend officer link (sender requests re-notification) ─────────

@forms_bp.route('/forms/resend-officer/<int:sub_id>', methods=['POST'])
@login_required
def resend_officer_link(sub_id):
    sub = FormSubmission.query.get_or_404(sub_id)

    # Only the original submitter or admin can resend
    is_admin = current_user.role and current_user.role.name == 'System Administrator'
    if sub.submitted_by != current_user.id and not is_admin:
        abort(403)

    if sub.status != 'pending':
        flash('This form is no longer pending.', 'error')
        return redirect(url_for('dashboard.view_submission', sub_id=sub_id))

    step = WorkflowStep.query.filter_by(
        form_type_id=sub.form_type_id, step_order=sub.current_step
    ).first()
    if not step:
        flash('Workflow step not found.', 'error')
        return redirect(url_for('dashboard.view_submission', sub_id=sub_id))

    tname   = sub.form_type.template_name
    officer = get_officer(tname, step.step_order)
    if not officer:
        flash('No officer configured for this step.', 'error')
        return redirect(url_for('dashboard.view_submission', sub_id=sub_id))

    # Invalidate all existing unused tokens for this step
    existing_tokens = OfficerToken.query.filter_by(
        submission_id=sub.id, step_order=sub.current_step, used=False
    ).all()
    for t in existing_tokens:
        t.used    = True
        t.used_at = datetime.now()
    db.session.commit()

    # Create a fresh token and resend
    notify_next_step(sub, step)

    db.session.add(AuditLog(
        user_id=current_user.id,
        action='OFFICER_LINK_RESENT',
        details=f'{current_user.full_name} resent officer link for step {sub.current_step} of {sub.tracking_number} to {officer["email"]}',
        ip_address=request.remote_addr
    ))
    db.session.commit()

    flash(f'A new review link has been sent to {officer["name"]} ({officer["email"]}).', 'success')
    return redirect(url_for('dashboard.view_submission', sub_id=sub_id))


# ── Authenticated (Sender / Admin) routes ─────────────────────────

@forms_bp.route('/forms/select')
@login_required
def select_form():
    form_types = FormType.query.filter_by(is_active=True).all()
    return render_template('forms/select_form.html', form_types=form_types)

@forms_bp.route('/forms/new/<int:form_type_id>', methods=['GET', 'POST'])
@login_required
def new_form(form_type_id):
    form_type = FormType.query.get_or_404(form_type_id)

    if request.method == 'POST':
        form_data  = {k: v for k, v in request.form.items() if k != 'csrf_token'}
        first_step = WorkflowStep.query.filter_by(
            form_type_id=form_type_id, step_order=1
        ).first()
        tracking_num = FormSubmission.generate_tracking_number(form_type.ref_number)
        sub = FormSubmission(
            tracking_number=tracking_num,
            form_type_id=form_type_id,
            submitted_by=current_user.id,
            current_step=1,
            current_department_id=first_step.department_id if first_step else None,
            status='pending',
            form_data=json.dumps(form_data)
        )
        db.session.add(sub)
        db.session.commit()
        db.session.add(AuditLog(
            user_id=current_user.id, action='FORM_SUBMITTED',
            details=f'Submitted {form_type.name}, tracking: {tracking_num}',
            ip_address=request.remote_addr
        ))
        db.session.commit()
        if first_step:
            notify_next_step(sub, first_step)
        flash(f'Form submitted! Tracking: {tracking_num}. The first officer has been notified.', 'success')
        return redirect(url_for('dashboard.view_submission', sub_id=sub.id))

    officers = OFFICERS.get(form_type.template_name, {})
    return render_template(f'forms/{form_type.template_name}_form.html',
                           form_type=form_type, user=current_user,
                           mode='new', officers=officers, sub=None, form_data={})


# ── Admin override approve ─────────────────────────────────────────

@forms_bp.route('/forms/admin-approve/<int:sub_id>', methods=['POST'])
@login_required
def admin_approve(sub_id):
    is_admin = current_user.role and current_user.role.name == 'System Administrator'
    if not is_admin:
        abort(403)
    sub = FormSubmission.query.get_or_404(sub_id)
    if sub.status != 'pending':
        flash('Form is not pending.', 'error')
        return redirect(url_for('dashboard.view_submission', sub_id=sub_id))
    step = WorkflowStep.query.filter_by(
        form_type_id=sub.form_type_id, step_order=sub.current_step
    ).first()
    approval = Approval(
        submission_id=sub.id,
        approved_by=current_user.id,
        officer_name=current_user.full_name,
        officer_email=current_user.email,
        step_number=sub.current_step,
        step_name=step.step_name if step else '',
        comment='[Admin override]',
        ip_address=request.remote_addr,
        verified_name=current_user.full_name,
    )
    db.session.add(approval)
    db.session.add(AuditLog(
        user_id=current_user.id,
        action='ADMIN_APPROVED',
        details=f'{current_user.full_name} admin-approved step {sub.current_step} of {sub.tracking_number}',
        ip_address=request.remote_addr
    ))
    # Notify submitter of admin action
    _create_notification(sub, sub.submitted_by,
        f"An admin approved step {sub.current_step} of your {sub.form_type.name} (Tracking: {sub.tracking_number}).")
    next_step = WorkflowStep.query.filter_by(
        form_type_id=sub.form_type_id, step_order=sub.current_step + 1
    ).first()
    if next_step:
        sub.current_step         += 1
        sub.current_department_id = next_step.department_id
        db.session.commit()
        notify_next_step(sub, next_step)
        flash('Step approved. Next officer notified.', 'success')
    else:
        sub.status       = 'approved'
        sub.completed_at = datetime.now()
        db.session.commit()
        submitter = User.query.get(sub.submitted_by)
        if submitter:
            notify_sender(submitter,
                f"[Mzuzu University DTS] Form Fully Approved – {sub.tracking_number}",
                f"""<html><body style="font-family:Arial,sans-serif;padding:30px;">
                <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
                            padding:32px;border:1px solid #e0e0e0;">
                  <h2 style="color:#1a3a5c;">Mzuzu University DTS</h2>
                  <p>Dear <strong>{submitter.full_name}</strong>,</p>
                  <p style="color:#2e7d32;font-weight:bold;">[APPROVED] Your form has been fully approved.</p>
                  <p><strong>Form:</strong> {sub.form_type.name}<br>
                     <strong>Tracking:</strong> {sub.tracking_number}</p>
                </div></body></html>""")
        flash('Form fully approved.', 'success')
    return redirect(url_for('dashboard.view_submission', sub_id=sub_id))

@forms_bp.route('/forms/reject/<int:sub_id>', methods=['POST'])
@login_required
def reject_form(sub_id):
    is_admin = current_user.role and current_user.role.name == 'System Administrator'
    if not is_admin:
        abort(403)
    sub = FormSubmission.query.get_or_404(sub_id)
    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('Please provide a reason.', 'error')
        return redirect(url_for('dashboard.view_submission', sub_id=sub_id))
    step = WorkflowStep.query.filter_by(
        form_type_id=sub.form_type_id, step_order=sub.current_step
    ).first()
    db.session.add(Rejection(
        submission_id=sub.id,
        rejected_by=current_user.id,
        officer_name=current_user.full_name,
        officer_email=current_user.email,
        step_number=sub.current_step,
        step_name=step.step_name if step else '',
        reason=reason,
        ip_address=request.remote_addr,
    ))
    sub.status       = 'rejected'
    sub.completed_at = datetime.now()
    db.session.commit()
    submitter = User.query.get(sub.submitted_by)
    if submitter:
        notify_sender(submitter,
            f"[Mzuzu University DTS] Form Rejected – {sub.tracking_number}",
            f"""<html><body style="font-family:Arial,sans-serif;padding:30px;">
            <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
                        padding:32px;border:1px solid #e0e0e0;">
              <h2 style="color:#1a3a5c;">Mzuzu University DTS</h2>
              <p>Dear <strong>{submitter.full_name}</strong>,</p>
              <p style="color:#c62828;font-weight:bold;">[REJECTED] Your form has been rejected.</p>
              <p><strong>Form:</strong> {sub.form_type.name}<br>
                 <strong>Tracking:</strong> {sub.tracking_number}<br>
                 <strong>Reason:</strong> {reason}</p>
            </div></body></html>""")
    flash('Form rejected. Sender notified.', 'success')
    return redirect(url_for('dashboard.home'))
