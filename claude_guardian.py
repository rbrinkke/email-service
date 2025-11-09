# File: claude_guardian.py
# Claude Guardian for Email System

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp

from email_system import EmailConfig, EmailService


class EmailSystemGuardian:
    """Claude Guardian specifically for the email system"""

    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.redis = email_service.redis_client.redis
        self.monitoring_interval = 30  # seconds
        self.alert_thresholds = {
            "queue_high_critical": 100,
            "queue_medium_warning": 1000,
            "queue_low_warning": 10000,
            "failed_rate_critical": 0.1,  # 10% failure rate
            "rate_limit_critical": 0.9,  # 90% rate limit usage
        }
        self.health_history = []

    async def start_monitoring(self):
        """Start continuous monitoring"""
        logging.info("Claude Guardian: Email system monitoring started")

        while True:
            try:
                await self.check_system_health()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logging.error(f"Guardian monitoring error: {e}")
                await asyncio.sleep(60)  # Longer sleep on error

    async def check_system_health(self):
        """Comprehensive system health check"""
        stats = await self.email_service.get_stats()
        current_time = datetime.utcnow()

        health_report = {
            "timestamp": current_time.isoformat(),
            "queues": {
                "high": int(stats.get("queue_high", 0)),
                "medium": int(stats.get("queue_medium", 0)),
                "low": int(stats.get("queue_low", 0)),
            },
            "performance": {
                "sent_today": int(stats.get("sent", 0)),
                "failed_today": int(stats.get("failed", 0)),
            },
            "rate_limits": {},
            "alerts": [],
        }

        # Check rate limits
        for provider in self.email_service.config.rate_limits:
            tokens = stats.get(f"rate_{provider}_tokens")
            if tokens and tokens != "N/A":
                limit = self.email_service.config.rate_limits[provider]["bucket_size"]
                usage = 1 - (int(tokens) / limit)
                health_report["rate_limits"][provider] = {
                    "usage": usage,
                    "tokens_remaining": int(tokens),
                }

        # Analyze health and generate alerts
        await self.analyze_health(health_report)

        # Store health history
        self.health_history.append(health_report)
        if len(self.health_history) > 100:  # Keep last 100 reports
            self.health_history.pop(0)

        # Log summary
        total_queued = sum(health_report["queues"].values())
        failure_rate = self.calculate_failure_rate(health_report)

        logging.info(
            f"Guardian Health Check: "
            f"Queued={total_queued}, "
            f"Sent={health_report['performance']['sent_today']}, "
            f"Failed={health_report['performance']['failed_today']}, "
            f"FailRate={failure_rate:.2%}, "
            f"Alerts={len(health_report['alerts'])}"
        )

    async def analyze_health(self, health_report: Dict):
        """Analyze health metrics and generate alerts/actions"""
        alerts = []

        # Check queue depths
        if health_report["queues"]["high"] > self.alert_thresholds["queue_high_critical"]:
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "type": "high_priority_queue_backlog",
                    "message": f"High priority queue has {health_report['queues']['high']} emails",
                    "action": "scale_workers",
                }
            )
            await self.handle_queue_backlog("high")

        if health_report["queues"]["medium"] > self.alert_thresholds["queue_medium_warning"]:
            alerts.append(
                {
                    "severity": "WARNING",
                    "type": "medium_priority_queue_warning",
                    "message": f"Medium priority queue has {health_report['queues']['medium']} emails",
                    "action": "monitor_closely",
                }
            )

        # Check failure rate
        failure_rate = self.calculate_failure_rate(health_report)
        if failure_rate > self.alert_thresholds["failed_rate_critical"]:
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "type": "high_failure_rate",
                    "message": f"Failure rate is {failure_rate:.2%}",
                    "action": "investigate_providers",
                }
            )
            await self.handle_high_failure_rate()

        # Check rate limits
        for provider, data in health_report["rate_limits"].items():
            if data["usage"] > self.alert_thresholds["rate_limit_critical"]:
                alerts.append(
                    {
                        "severity": "WARNING",
                        "type": "rate_limit_high",
                        "message": f"{provider} rate limit at {data['usage']:.1%}",
                        "action": "switch_provider",
                    }
                )
                await self.handle_rate_limit_pressure(provider)

        health_report["alerts"] = alerts

        # Store alerts in Redis for dashboard
        if alerts:
            await self.redis.lpush(
                "email:alerts",
                json.dumps({"timestamp": health_report["timestamp"], "alerts": alerts}),
            )
            await self.redis.ltrim("email:alerts", 0, 50)  # Keep last 50 alerts

    def calculate_failure_rate(self, health_report: Dict) -> float:
        """Calculate current failure rate"""
        sent = health_report["performance"]["sent_today"]
        failed = health_report["performance"]["failed_today"]
        total = sent + failed

        if total == 0:
            return 0.0

        return failed / total

    async def handle_queue_backlog(self, priority: str):
        """Handle queue backlog by optimizing processing"""
        logging.warning(f"Guardian Action: Handling {priority} priority queue backlog")

        # Could trigger worker scaling, provider switching, etc.
        # For now, log the action
        await self.redis.hincrby("email:guardian_actions", f"queue_backlog_{priority}", 1)

    async def handle_high_failure_rate(self):
        """Handle high failure rate"""
        logging.error("Guardian Action: High failure rate detected - investigating providers")

        # Could implement provider health checks, circuit breaker adjustments, etc.
        await self.redis.hincrby("email:guardian_actions", "high_failure_rate", 1)

    async def handle_rate_limit_pressure(self, provider: str):
        """Handle rate limit pressure"""
        logging.warning(f"Guardian Action: Rate limit pressure on {provider}")

        # Could implement provider switching logic
        await self.redis.hincrby("email:guardian_actions", f"rate_limit_{provider}", 1)

    async def get_health_summary(self) -> Dict:
        """Get health summary for dashboard"""
        if not self.health_history:
            return {"status": "no_data"}

        latest = self.health_history[-1]

        # Calculate trends
        if len(self.health_history) >= 2:
            previous = self.health_history[-2]
            trends = {
                "queue_trend": sum(latest["queues"].values()) - sum(previous["queues"].values()),
                "failure_trend": self.calculate_failure_rate(latest)
                - self.calculate_failure_rate(previous),
            }
        else:
            trends = {"queue_trend": 0, "failure_trend": 0}

        return {
            "status": "healthy" if not latest["alerts"] else "issues_detected",
            "latest_check": latest["timestamp"],
            "total_queued": sum(latest["queues"].values()),
            "failure_rate": self.calculate_failure_rate(latest),
            "active_alerts": len(latest["alerts"]),
            "trends": trends,
            "provider_status": latest["rate_limits"],
        }

    async def self_heal_attempt(self, issue_type: str, context: Dict):
        """Attempt automated healing for common issues"""
        healing_actions = {
            "provider_down": self.heal_provider_failover,
            "rate_limit_exceeded": self.heal_rate_limit_backoff,
            "queue_overflow": self.heal_queue_management,
            "memory_pressure": self.heal_memory_cleanup,
        }

        if issue_type in healing_actions:
            try:
                await healing_actions[issue_type](context)
                logging.info(f"Guardian Self-Heal: Successfully handled {issue_type}")
                return True
            except Exception as e:
                logging.error(f"Guardian Self-Heal: Failed to handle {issue_type}: {e}")
                return False

        return False

    async def heal_provider_failover(self, context: Dict):
        """Automatically failover to backup provider"""
        failed_provider = context.get("provider")
        # Implementation would switch traffic to healthy provider
        logging.info(f"Self-healing: Failing over from {failed_provider}")

    async def heal_rate_limit_backoff(self, context: Dict):
        """Implement exponential backoff for rate-limited provider"""
        provider = context.get("provider")
        # Implementation would temporarily reduce rate for this provider
        logging.info(f"Self-healing: Applying rate limit backoff to {provider}")

    async def heal_queue_management(self, context: Dict):
        """Optimize queue processing during overflow"""
        # Implementation would prioritize critical emails, batch processing, etc.
        logging.info("Self-healing: Optimizing queue processing")

    async def heal_memory_cleanup(self, context: Dict):
        """Clean up memory during pressure"""
        # Implementation would clear caches, optimize data structures
        logging.info("Self-healing: Performing memory cleanup")
