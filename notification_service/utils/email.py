import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sendgrid
from sendgrid.helpers.mail import Mail

SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-password')
SENDER_EMAIL = 'shubhamghadgerocks@gmail.com'

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

def send_email(to_email, subject, content):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"Would send email to {to_email} with subject '{subject}': {content}")
        return True
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False 

def send_email_sendgrid(to_email, subject, content):
    SENDGRID_API_KEY = ""
    if not SENDGRID_API_KEY:
        print(f"[SendGrid] Would send email to {to_email} with subject '{subject}': {content}")
        return True
    try:
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        response = sg.send(message)
        print(f"[SendGrid] Email sent to {to_email}, status code: {response.status_code}")
        return response.status_code in [200, 202]
    except Exception as e:
        print(f"[SendGrid] Error sending email: {str(e)}")
        return False 