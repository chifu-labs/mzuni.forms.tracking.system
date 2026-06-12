from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.models import FormSubmission, Approval, Rejection, Notification, WorkflowStep, User, Department, Role
from extensions import db
from sqlalchemy import or_
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def home():
    role_name = current_user.role.name if current_user.role else ''

    if role_name == 'System Administrator':
        return redirect(url_for('admin.admin_home'))

    # Sender: see own submissions
    my_submissions = FormSubmission.query.filter_by(submitted_by=current_user.id).order_by(FormSubmission.submitted_at.desc()).all()

    # Department queue: forms assigned to current user's department or role
    dept_queue = []
    if role_name not in ['Sender']:
        all_submissions = FormSubmission.query.filter(
            FormSubmission.status == 'pending'
        ).order_by(FormSubmission.submitted_at.desc()).all()

        for sub in all_submissions:
            steps = WorkflowStep.query.filter_by(
                form_type_id=sub.form_type_id,
                step_order=sub.current_step
            ).first()
            if steps:
                dept_match = steps.department_id and steps.department_id == current_user.department_id
                role_match = steps.role_id and steps.role_id == current_user.role_id
                if dept_match or role_match:
                    dept_queue.append(sub)

    unread_notifications = Notification.query.filter_by(
        recipient_id=current_user.id, is_read=False
    ).count()

    return render_template('dashboard/home.html',
                           my_submissions=my_submissions,
                           dept_queue=dept_queue,
                           unread_notifications=unread_notifications,
                           role_name=role_name)

@dashboard_bp.route('/dashboard/submission/<int:sub_id>')
@login_required
def view_submission(sub_id):
    sub = FormSubmission.query.get_or_404(sub_id)
    role_name = current_user.role.name if current_user.role else ''

    # Access control
    is_submitter = sub.submitted_by == current_user.id
    is_admin = role_name == 'System Administrator'

    # Check if current user is in the workflow for this submission
    is_in_workflow = False
    current_step_obj = WorkflowStep.query.filter_by(
        form_type_id=sub.form_type_id, step_order=sub.current_step
    ).first()
    if current_step_obj:
        dept_match = current_step_obj.department_id and current_step_obj.department_id == current_user.department_id
        role_match = current_step_obj.role_id and current_step_obj.role_id == current_user.role_id
        is_in_workflow = dept_match or role_match

    if not (is_submitter or is_admin or is_in_workflow):
        # Check if user approved any step of this submission
        # Officer approvals have approved_by=NULL (they use tokens), so also check by email
        approved = Approval.query.filter(
            Approval.submission_id == sub.id,
            or_(
                Approval.approved_by == current_user.id,
                Approval.officer_email == current_user.email
            )
        ).first()
        if not approved:
            flash('You do not have permission to view this submission.', 'danger')
            return redirect(url_for('dashboard.home'))

    form_data = json.loads(sub.form_data) if sub.form_data else {}
    approvals = Approval.query.filter_by(submission_id=sub.id).order_by(Approval.step_number).all()
    rejections = Rejection.query.filter_by(submission_id=sub.id).order_by(Rejection.rejected_at).all()
    all_steps = WorkflowStep.query.filter_by(form_type_id=sub.form_type_id).order_by(WorkflowStep.step_order).all()

    return render_template('dashboard/view_submission.html',
                           sub=sub,
                           form_data=form_data,
                           approvals=approvals,
                           rejections=rejections,
                           all_steps=all_steps,
                           is_submitter=is_submitter,
                           is_in_workflow=is_in_workflow,
                           current_step_obj=current_step_obj)

@dashboard_bp.route('/dashboard/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('dashboard/notifications.html', notifications=notifs)

@dashboard_bp.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('dashboard/profile.html')

@dashboard_bp.route('/dashboard/track', methods=['GET', 'POST'])
@login_required
def track():
    sub = None
    if request.method == 'POST':
        tracking_number = request.form.get('tracking_number', '').strip()
        sub = FormSubmission.query.filter_by(tracking_number=tracking_number).first()
        if not sub:
            flash('No submission found with that tracking number.', 'warning')
        elif sub.submitted_by != current_user.id:
            role_name = current_user.role.name if current_user.role else ''
            if role_name != 'System Administrator':
                flash('You can only track your own submissions.', 'danger')
                sub = None
    return render_template('dashboard/track.html', sub=sub)
