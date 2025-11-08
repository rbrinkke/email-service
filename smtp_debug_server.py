#!/usr/bin/env python3
"""
Simple SMTP Debugging Server
This server receives emails and displays them in the console
Acts as a lightweight alternative to MailHog for testing
"""

import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as Server
from email import message_from_bytes
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailDebugHandler:
    """Handler that prints received emails"""

    def __init__(self):
        self.email_count = 0

    async def handle_DATA(self, server, session, envelope):
        """Handle incoming email data"""
        self.email_count += 1

        print("\n" + "="*70)
        print(f"📧 Email #{self.email_count} Received at {datetime.now().isoformat()}")
        print("="*70)
        print(f"From: {envelope.mail_from}")
        print(f"To: {', '.join(envelope.rcpt_tos)}")
        print("-"*70)

        # Parse email message
        try:
            msg = message_from_bytes(envelope.content)

            # Print headers
            print(f"Subject: {msg.get('Subject', 'No subject')}")
            print(f"Date: {msg.get('Date', 'No date')}")
            print(f"Content-Type: {msg.get_content_type()}")
            print("-"*70)

            # Print body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        print("\n[TEXT CONTENT]")
                        print(part.get_payload(decode=True).decode('utf-8', errors='ignore'))
                    elif content_type == "text/html":
                        print("\n[HTML CONTENT]")
                        html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        print(html_content[:500] + "..." if len(html_content) > 500 else html_content)
            else:
                print("\n[CONTENT]")
                print(msg.get_payload(decode=True).decode('utf-8', errors='ignore'))

        except Exception as e:
            print(f"Error parsing email: {e}")
            print("\n[RAW CONTENT]")
            print(envelope.content.decode('utf-8', errors='ignore'))

        print("="*70)
        print(f"✅ Total emails received: {self.email_count}\n")

        return '250 OK'

def run_smtp_server(host='0.0.0.0', port=1025):
    """Run the SMTP debugging server"""

    handler = EmailDebugHandler()
    controller = Controller(handler, hostname=host, port=port)

    print("\n" + "="*70)
    print("🚀 SMTP Debugging Server Starting")
    print("="*70)
    print(f"Listening on: {host}:{port}")
    print("Press Ctrl+C to stop")
    print("="*70 + "\n")

    controller.start()

    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print(f"📊 SMTP Server Stopping - Total emails received: {handler.email_count}")
        print("="*70)
        controller.stop()

if __name__ == '__main__':
    import sys

    # Parse arguments
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1025

    run_smtp_server(host, port)
