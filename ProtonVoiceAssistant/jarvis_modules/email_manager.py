"""
Jarvis Email Management Module
Handles reading, sending, and checking emails
"""
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json

class EmailManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "data", "email_config.json")
        self.load_config()
    
    def load_config(self):
        """Load email configuration from file"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "email": "",
                "password": ""
            }
            self.save_config()
    
    def save_config(self):
        """Save email configuration to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_email(self, email_address, password):
        """Setup email credentials"""
        self.config["email"] = email_address
        self.config["password"] = password
        self.save_config()
        return "Email configured successfully"
    
    def send_email(self, to_email, subject, body):
        """Send an email"""
        try:
            if not self.config.get("email") or not self.config.get("password"):
                return "Email not configured. Please set up your email first."
            
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])
            server.starttls()
            server.login(self.config["email"], self.config["password"])
            server.send_message(msg)
            server.quit()
            
            return f"Email sent successfully to {to_email}"
        except Exception as e:
            return f"Failed to send email: {str(e)}"
    
    def check_emails(self, num_emails=5):
        """Check and return recent emails"""
        try:
            if not self.config.get("email") or not self.config.get("password"):
                return "Email not configured. Please set up your email first."
            
            mail = imaplib.IMAP4_SSL(self.config["imap_server"], self.config["imap_port"])
            mail.login(self.config["email"], self.config["password"])
            mail.select("inbox")
            
            _, message_numbers = mail.search(None, "ALL")
            message_numbers = message_numbers[0].split()
            
            emails = []
            for num in message_numbers[-num_emails:]:
                _, msg_data = mail.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                emails.append({
                    "from": email_message["From"],
                    "subject": email_message["Subject"],
                    "date": email_message["Date"]
                })
            
            mail.close()
            mail.logout()
            
            if not emails:
                return "No new emails found."
            
            result = f"You have {len(emails)} recent emails:\n"
            for i, email_info in enumerate(emails, 1):
                result += f"{i}. From: {email_info['from']}, Subject: {email_info['subject']}\n"
            
            return result
        except Exception as e:
            return f"Failed to check emails: {str(e)}"
    
    def read_latest_email(self):
        """Read the latest email"""
        try:
            if not self.config.get("email") or not self.config.get("password"):
                return "Email not configured."
            
            mail = imaplib.IMAP4_SSL(self.config["imap_server"], self.config["imap_port"])
            mail.login(self.config["email"], self.config["password"])
            mail.select("inbox")
            
            _, message_numbers = mail.search(None, "ALL")
            message_numbers = message_numbers[0].split()
            
            if not message_numbers:
                return "No emails found."
            
            latest = message_numbers[-1]
            _, msg_data = mail.fetch(latest, "(RFC822)")
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            subject = email_message["Subject"]
            from_addr = email_message["From"]
            
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = email_message.get_payload(decode=True).decode()
            
            mail.close()
            mail.logout()
            
            return f"Latest email from {from_addr}, Subject: {subject}\n\n{body[:500]}"
        except Exception as e:
            return f"Failed to read email: {str(e)}"


