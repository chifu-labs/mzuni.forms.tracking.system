from flask_mail import Message
from extensions import mail
from flask import url_for

def send_notification_email(recipient_email, recipient_name, form_type_name, tracking_number, description, department_action, login_url):
    try:
        msg = Message(
            subject=f'[Mzuzu University DTS] Action Required: {form_type_name}',
            recipients=[recipient_email]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a3a5c; color: white; padding: 20px; text-align: center;">
                <h2>MZUZU UNIVERSITY</h2>
                <p>Digital Document Tracking and Approval System</p>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <p>Dear {recipient_name},</p>
                <p>A document has been routed to your department/role and requires your action.</p>
                <table style="width:100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background:#e8f0fe;">
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Form Type</td>
                        <td style="padding:10px; border:1px solid #ddd;">{form_type_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Tracking Number</td>
                        <td style="padding:10px; border:1px solid #ddd;">{tracking_number}</td>
                    </tr>
                    <tr style="background:#e8f0fe;">
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Description</td>
                        <td style="padding:10px; border:1px solid #ddd;">{description}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Action Required</td>
                        <td style="padding:10px; border:1px solid #ddd;">{department_action}</td>
                    </tr>
                </table>
                <p>Please log in to the system to review and take action on this document.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{login_url}" style="background:#1a3a5c; color:white; padding:12px 30px; text-decoration:none; border-radius:5px; font-weight:bold;">
                        LOG IN TO DTS
                    </a>
                </div>
                <p style="color:#666; font-size:12px;">This is an automated notification from Mzuzu University Digital Tracking System. Please do not reply to this email.</p>
            </div>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email send error: {e}")

def send_rejection_email(recipient_email, recipient_name, form_type_name, tracking_number, rejection_reason, rejected_by, step_name):
    try:
        msg = Message(
            subject=f'[Mzuzu University DTS] Form Rejected: {tracking_number}',
            recipients=[recipient_email]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #c0392b; color: white; padding: 20px; text-align: center;">
                <h2>MZUZU UNIVERSITY</h2>
                <p>Digital Document Tracking and Approval System</p>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <p>Dear {recipient_name},</p>
                <p style="color:#c0392b; font-weight:bold;">Your form has been rejected.</p>
                <table style="width:100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background:#fde8e8;">
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Form Type</td>
                        <td style="padding:10px; border:1px solid #ddd;">{form_type_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Tracking Number</td>
                        <td style="padding:10px; border:1px solid #ddd;">{tracking_number}</td>
                    </tr>
                    <tr style="background:#fde8e8;">
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Rejected At Stage</td>
                        <td style="padding:10px; border:1px solid #ddd;">{step_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Rejected By</td>
                        <td style="padding:10px; border:1px solid #ddd;">{rejected_by}</td>
                    </tr>
                    <tr style="background:#fde8e8;">
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Reason for Rejection</td>
                        <td style="padding:10px; border:1px solid #ddd;">{rejection_reason}</td>
                    </tr>
                </table>
                <p>Please log in to the system for more details.</p>
            </div>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email send error: {e}")

def send_password_reset_email(recipient_email, recipient_name, reset_link):
    try:
        msg = Message(
            subject='[Mzuzu University DTS] Password Reset Request',
            recipients=[recipient_email]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a3a5c; color: white; padding: 20px; text-align: center;">
                <h2>MZUZU UNIVERSITY</h2>
                <p>Digital Document Tracking and Approval System</p>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <p>Dear {recipient_name},</p>
                <p>You requested a password reset. Click the button below to reset your password. This link expires in 1 hour.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background:#1a3a5c; color:white; padding:12px 30px; text-decoration:none; border-radius:5px; font-weight:bold;">
                        RESET PASSWORD
                    </a>
                </div>
                <p>If you did not request this, please ignore this email.</p>
            </div>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email send error: {e}")

def send_completion_email(recipient_email, recipient_name, form_type_name, tracking_number):
    try:
        msg = Message(
            subject=f'[Mzuzu University DTS] Form Fully Approved: {tracking_number}',
            recipients=[recipient_email]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #27ae60; color: white; padding: 20px; text-align: center;">
                <h2>MZUZU UNIVERSITY</h2>
                <p>Digital Document Tracking and Approval System</p>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <p>Dear {recipient_name},</p>
                <p style="color:#27ae60; font-weight:bold;">Your form has been fully approved and processed.</p>
                <table style="width:100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background:#e8fde8;">
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Form Type</td>
                        <td style="padding:10px; border:1px solid #ddd;">{form_type_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Tracking Number</td>
                        <td style="padding:10px; border:1px solid #ddd;">{tracking_number}</td>
                    </tr>
                </table>
                <p>Please log in to the system to view the fully approved form.</p>
            </div>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email send error: {e}")
