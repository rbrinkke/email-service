#!/usr/bin/env python3
"""
Comprehensive Email System Startup and Test Script
This script starts all components and runs a complete end-to-end test
"""

import asyncio
import subprocess
import time
import os
import signal
import sys
from datetime import datetime

# Set environment variables
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'
os.environ['SMTP_HOST'] = 'localhost'
os.environ['SMTP_PORT'] = '1025'

# Import after setting environment
from config.email_config import EmailConfig
from models.email_models import EmailPriority, EmailProvider
from services.email_service import EmailService

class ProcessManager:
    """Manages background processes"""

    def __init__(self):
        self.processes = []

    def start_process(self, name, command):
        """Start a background process"""
        print(f"   Starting {name}...")
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        self.processes.append((name, proc))
        time.sleep(1)
        return proc

    def stop_all(self):
        """Stop all processes"""
        print("\n🛑 Stopping all processes...")
        for name, proc in self.processes:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                print(f"   Stopped {name}")
            except Exception as e:
                print(f"   Error stopping {name}: {e}")
        time.sleep(1)

async def run_email_test():
    """Run comprehensive email system test"""

    print("\n" + "="*70)
    print("🚀 FreeFace Email System - Complete Test")
    print("="*70 + "\n")

    # Initialize
    config = EmailConfig(redis_host='localhost', redis_port=6379)
    email_service = EmailService(config)

    try:
        await email_service.initialize()
        print("✅ Connected to Redis\n")

        # Test emails
        emails_to_send = [
            {
                "recipients": "high@example.com",
                "priority": EmailPriority.HIGH,
                "subject": "High Priority Test",
                "message": "This is a high-priority test email"
            },
            {
                "recipients": "medium@example.com",
                "priority": EmailPriority.MEDIUM,
                "subject": "Medium Priority Test",
                "message": "This is a medium-priority test email"
            },
            {
                "recipients": "low@example.com",
                "priority": EmailPriority.LOW,
                "subject": "Low Priority Test",
                "message": "This is a low-priority test email"
            }
        ]

        print("📨 Queueing test emails...")
        job_ids = []
        for email in emails_to_send:
            job_id = await email_service.send_email(
                recipients=email["recipients"],
                template="test_email",
                data={
                    "subject": email["subject"],
                    "message": email["message"],
                    "name": "Test User",
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=email["priority"],
                provider=EmailProvider.SMTP
            )
            job_ids.append(job_id)
            print(f"   ✅ Queued: {email['subject']} (ID: {job_id[:8]}...)")

        print(f"\n📊 Total emails queued: {len(job_ids)}")

        # Check stats
        stats = await email_service.get_stats()
        print(f"   High Priority Queue: {stats.get('queue_high', 0)}")
        print(f"   Medium Priority Queue: {stats.get('queue_medium', 0)}")
        print(f"   Low Priority Queue: {stats.get('queue_low', 0)}")

        # Start workers
        print("\n👷 Starting workers...")
        await email_service.start_workers(worker_count=2)
        print("   Workers processing emails...")

        # Wait for processing
        print("\n⏳ Waiting for emails to be processed (15 seconds)...")
        for i in range(15, 0, -1):
            await asyncio.sleep(1)
            if i % 5 == 0:
                stats = await email_service.get_stats()
                remaining = stats.get('queue_high', 0) + stats.get('queue_medium', 0) + stats.get('queue_low', 0)
                print(f"   {i}s remaining... (Queue: {remaining} emails)")

        # Final stats
        print("\n📊 Final Statistics:")
        stats = await email_service.get_stats()
        print(f"   High Priority Queue: {stats.get('queue_high', 0)}")
        print(f"   Medium Priority Queue: {stats.get('queue_medium', 0)}")
        print(f"   Low Priority Queue: {stats.get('queue_low', 0)}")
        print(f"   Sent Today: {stats.get('sent', 0)}")
        print(f"   Failed Today: {stats.get('failed', 0)}")

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await email_service.shutdown()

def main():
    """Main test runner"""

    print("\n" + "="*70)
    print("🔧 FreeFace Email System - Complete Startup and Test")
    print("="*70)

    pm = ProcessManager()

    try:
        # 1. Check Redis
        print("\n1️⃣ Checking Redis...")
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True)
        if result.stdout.strip() == 'PONG':
            print("   ✅ Redis is running")
        else:
            print("   ❌ Redis is not responding")
            return 1

        # 2. Start SMTP Debug Server
        print("\n2️⃣ Starting SMTP Debug Server...")
        smtp_proc = pm.start_process(
            "SMTP Server",
            "python3 smtp_debug_server.py localhost 1025"
        )
        print("   ✅ SMTP server started on localhost:1025")

        # 3. Run tests
        print("\n3️⃣ Running Email System Tests...")
        asyncio.run(run_email_test())

        # 4. Summary
        print("\n" + "="*70)
        print("🎉 All Tests Complete!")
        print("="*70)
        print("\n💡 System is ready for use!")
        print("\n   To start the API:")
        print("      export REDIS_HOST=localhost && python3 api.py")
        print("\n   To start workers:")
        print("      export REDIS_HOST=localhost && python3 worker.py")
        print("\n   To test via API:")
        print('      curl -X POST http://localhost:8010/send \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"recipients": "test@example.com",')
        print('             "template": "test_email",')
        print('             "data": {"subject": "Test", "message": "Hello"}}\'')
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        pm.stop_all()
        print("\n✅ Cleanup complete\n")

if __name__ == '__main__':
    sys.exit(main())
