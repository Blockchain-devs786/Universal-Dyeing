"""Email service for license activation"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import re
from typing import Optional, Tuple
from common.config import (
    EMAIL_ADDRESS, EMAIL_APP_PASSWORD, EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT, EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT
)


class EmailService:
    """Handles email sending and receiving for license activation"""
    
    def __init__(self):
        self.email_address = EMAIL_ADDRESS
        self.app_password = EMAIL_APP_PASSWORD
    
    def send_license_request(self, machine_id: str) -> bool:
        """Send license request email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = self.email_address
            msg['Subject'] = f"TMS License Request - {machine_id[:8]}"
            
            body = f"""
TMS License Activation Request

Machine ID: {machine_id}
Request Date: {email.utils.formatdate()}

Please reply with the number of validity days.
Format: VALIDITY: <number>
Example: VALIDITY: 365
"""
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
            server.starttls()
            server.login(self.email_address, self.app_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def check_for_reply(self, machine_id: str) -> Optional[int]:
        """Check inbox for license reply and extract validity days"""
        try:
            mail = imaplib.IMAP4_SSL(EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT)
            mail.login(self.email_address, self.app_password)
            mail.select('inbox')
            
            # Search for unread emails with subject containing machine ID
            search_criteria = f'(UNSEEN SUBJECT "TMS License")'
            status, messages = mail.search(None, search_criteria)
            
            if status != 'OK':
                mail.logout()
                return None
            
            email_ids = messages[0].split()
            
            # Check most recent emails
            for email_id in reversed(email_ids[-10:]):  # Check last 10 emails
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Decode subject
                subject = email_message['Subject']
                if isinstance(subject, bytes):
                    subject = decode_header(subject)[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                
                # Check if this is a reply to our request
                if machine_id[:8] not in subject:
                    continue
                
                # Extract body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                # Look for validity pattern
                pattern = r'VALIDITY:\s*(\d+)'
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    validity_days = int(match.group(1))
                    mail.logout()
                    return validity_days
            
            mail.logout()
            return None
        except Exception as e:
            print(f"Error checking email: {e}")
            return None

