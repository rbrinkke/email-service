# File: monitor.py
# Email System Monitoring Dashboard

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import os
from datetime import datetime, timedelta
from email_system import EmailService, EmailConfig

app = FastAPI(title="FreeFace Email Monitor")
templates = Jinja2Templates(directory="templates")

# Initialize email service for monitoring
config = EmailConfig(
    redis_host=os.getenv('REDIS_HOST', '10.10.1.21'),
    redis_port=int(os.getenv('REDIS_PORT', 6379))
)
email_service = EmailService(config)

@app.on_event("startup")
async def startup_event():
    await email_service.initialize()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main monitoring dashboard"""
    stats = await email_service.get_stats()
    
    # Calculate additional metrics
    total_queued = (
        int(stats.get('queue_high', 0)) +
        int(stats.get('queue_medium', 0)) +
        int(stats.get('queue_low', 0))
    )
    
    sent_today = int(stats.get('sent', 0))
    failed_today = int(stats.get('failed', 0))
    success_rate = (sent_today / max(1, sent_today + failed_today)) * 100
    
    # Rate limit status
    rate_status = {}
    for provider, limits in config.rate_limits.items():
        tokens = stats.get(f'rate_{provider}_tokens', 'N/A')
        if tokens != 'N/A':
            utilization = (1 - int(tokens) / limits['bucket_size']) * 100
            rate_status[provider] = {
                'tokens': tokens,
                'limit': limits['bucket_size'],
                'utilization': f"{utilization:.1f}%"
            }
        else:
            rate_status[provider] = {
                'tokens': 'N/A',
                'limit': limits['bucket_size'],
                'utilization': 'N/A'
            }
    
    dashboard_data = {
        'total_queued': total_queued,
        'queue_high': stats.get('queue_high', 0),
        'queue_medium': stats.get('queue_medium', 0),
        'queue_low': stats.get('queue_low', 0),
        'sent_today': sent_today,
        'failed_today': failed_today,
        'success_rate': f"{success_rate:.1f}%",
        'rate_status': rate_status,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": dashboard_data}
    )

@app.get("/api/stats")
async def api_stats():
    """JSON API for real-time stats"""
    return await email_service.get_stats()

@app.get("/api/dead-letter")
async def dead_letter_queue():
    """Get dead letter queue contents"""
    redis = email_service.redis_client.redis
    dead_letters = await redis.lrange("email:dead_letter", 0, 50)
    
    jobs = []
    for job_data in dead_letters:
        try:
            job = json.loads(job_data)
            jobs.append(job)
        except json.JSONDecodeError:
            continue
    
    return {"dead_letter_jobs": jobs, "count": len(jobs)}
