"""
Run this to test if Gmail sending works.
Usage: python test_email.py your@email.com
"""
import sys, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

MAIL_USERNAME = "chifulabs@gmail.com"
MAIL_PASSWORD = "ysxy ciut yhqm aiwe"

to_email = sys.argv[1] if len(sys.argv) > 1 else MAIL_USERNAME

print(f"Sending test email to: {to_email}")
print(f"From account: {MAIL_USERNAME}")
print("Connecting to smtp.gmail.com:587 ...")

try:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "✅ Mzuzu DTS — Email Test"
    msg["From"]    = f"Mzuzu University DTS <{MAIL_USERNAME}>"
    msg["To"]      = to_email
    msg.attach(MIMEText("""
    <html><body style="font-family:Arial,sans-serif;padding:30px;">
        <h2 style="color:#1a3a5c;">Mzuzu University DTS</h2>
        <p>✅ Email is working correctly! Your system can send notifications.</p>
    </body></html>
    """, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.ehlo()
        s.starttls()
        s.login(MAIL_USERNAME, MAIL_PASSWORD)
        s.sendmail(MAIL_USERNAME, to_email, msg.as_string())

    print(f"\n✅ SUCCESS! Email sent to {to_email}")
    print("Check your inbox (and spam folder).")

except smtplib.SMTPAuthenticationError:
    print("\n AUTHENTICATION FAILED!")
    print("   The Gmail App Password is wrong or expired.")
    print("   Go to: https://myaccount.google.com/apppasswords")
    print("   Generate a new App Password and update .env")

except smtplib.SMTPException as e:
    print(f"\n SMTP ERROR!: {e}")

except Exception as e:
    print(f"\n ERROR!: {e}")
