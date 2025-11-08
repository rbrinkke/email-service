# File: monitor.py
# Email System Monitoring Dashboard

import json
import logging
import os
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config.logging_config import setup_logging
from email_system import EmailService, EmailConfig
from services.audit_service import audit_trail

# Configure logging using centralized configuration
# This sets up Docker-compatible logging (stdout/stderr only)
# Respects LOG_LEVEL, ENVIRONMENT, and other logging env vars
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)

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

    # Initialize audit trail with Redis client
    audit_trail.set_redis_client(email_service.redis_client)
    logger.info("Audit trail initialized for monitoring")

    logger.info("Email monitoring dashboard started")

@app.on_event("shutdown")
async def shutdown_event():
    await email_service.shutdown()
    logger.info("Email monitoring dashboard stopped")

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

@app.get("/api/service-metrics")
async def service_metrics():
    """
    Get per-service usage metrics

    Returns metrics for all services that have called the email API:
    - Total API calls
    - Total emails sent
    - Calls today
    - Per-endpoint breakdown

    Example response:
    {
        "main-app": {
            "total_calls": 1247,
            "total_emails": 5623,
            "calls_today": 45,
            "endpoints": {
                "/send": 800,
                "/send/welcome": 300,
                "/send/password-reset": 100,
                "/stats": 47
            }
        },
        "user-service": { ... }
    }
    """
    try:
        metrics = await audit_trail.get_all_services_metrics()
        return {
            "services": metrics,
            "total_services": len(metrics),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get service metrics: {e}")
        return {
            "services": {},
            "total_services": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/service-metrics/{service_name}")
async def service_metrics_detail(service_name: str):
    """
    Get detailed metrics for a specific service

    Args:
        service_name: Service identifier (e.g., "main-app")

    Returns detailed usage metrics for the specified service
    """
    try:
        metrics = await audit_trail.get_service_metrics(service_name)

        if not metrics:
            return {
                "service": service_name,
                "error": "Service not found or no metrics available",
                "timestamp": datetime.now().isoformat()
            }

        return {
            "service": service_name,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get metrics for service {service_name}: {e}")
        return {
            "service": service_name,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/audit/{job_id}")
async def job_audit(job_id: str):
    """
    Get audit record for a specific email job

    Args:
        job_id: Email job identifier

    Returns audit information including which service sent the email

    Example response:
    {
        "job_id": "job_abc123",
        "audit": {
            "service": "main-app",
            "endpoint": "/send",
            "timestamp": "2025-11-08T14:30:00",
            "template": "welcome",
            "recipient_count": 1
        }
    }
    """
    try:
        audit = await audit_trail.get_job_audit(job_id)

        if not audit:
            return {
                "job_id": job_id,
                "audit": None,
                "error": "Audit record not found (job may be older than 30 days)",
                "timestamp": datetime.now().isoformat()
            }

        return {
            "job_id": job_id,
            "audit": audit,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get audit for job {job_id}: {e}")
        return {
            "job_id": job_id,
            "audit": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
