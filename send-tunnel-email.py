#!/usr/bin/env python3
"""
Send tunnel URL notification email
"""
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_email(tunnel_url):
    """Send email with tunnel URL"""
    email_to = os.getenv('EMAIL_TO', '').strip()

    # Skip if no email configured
    if not email_to:
        print("Email notifications disabled (EMAIL_TO not set)")
        return True

    email_from = os.getenv('EMAIL_FROM', 'agent-remote-access@noreply.com')
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')

    # Check if SMTP credentials are provided
    if smtp_user and smtp_password:
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_from
            msg['To'] = email_to
            msg['Subject'] = f'Agent Remote Access Tunnel Started'

            # Email body
            body = f"""
Agent Remote Access Tunnel is now running!

Access URL: {tunnel_url}
Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Login credentials are in your .env file.

This tunnel will be active until you stop it with ./stop.sh

---
Sent by agent-remote-access
"""

            msg.attach(MIMEText(body, 'plain'))

            # Send via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            print(f"✓ Email sent to {email_to}")
            return True

        except Exception as e:
            print(f"✗ Failed to send email: {e}")
            print(f"  (You can still access the tunnel at: {tunnel_url})")
            return False
    else:
        # No SMTP credentials - use macOS mail command as fallback
        try:
            body = f"Agent Remote Access Tunnel: {tunnel_url}\n\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            import subprocess
            result = subprocess.run(
                ['mail', '-s', 'Agent Remote Access Tunnel Started', email_to],
                input=body.encode(),
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                print(f"✓ Email sent to {email_to} via mail command")
                return True
            else:
                print(f"✗ Could not send email (mail command failed)")
                print(f"  Configure SMTP_USER and SMTP_PASSWORD in .env for email notifications")
                print(f"  Tunnel URL: {tunnel_url}")
                return False

        except Exception as e:
            print(f"✗ Email not sent: {e}")
            print(f"  Configure SMTP settings in .env for email notifications")
            print(f"  Tunnel URL: {tunnel_url}")
            return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: send-tunnel-email.py <tunnel_url>")
        sys.exit(1)

    tunnel_url = sys.argv[1]
    success = send_email(tunnel_url)
    sys.exit(0 if success else 1)
