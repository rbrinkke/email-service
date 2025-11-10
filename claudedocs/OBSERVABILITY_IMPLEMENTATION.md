# Email Service Observability Implementation

## Overview

This document details the comprehensive observability implementation for the email-service, integrating with the existing Activity App observability stack (Prometheus, Loki, Grafana, AlertManager).

**Implementation Date**: 2025-11-10
**Status**: ✅ Complete
**Approach**: Best-of-class production-grade observability following industry standards

## Architecture

### Observability Stack Integration

```
┌─────────────────────────────────────────────────────────────┐
│                   Observability Stack                        │
│  ┌──────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐ │
│  │  Prometheus  │  │   Loki   │  │ Grafana │  │AlertMgr  │ │
│  │   :9091      │  │  :3100   │  │  :3002  │  │  :9093   │ │
│  └──────┬───────┘  └─────┬────┘  └────┬────┘  └────┬─────┘ │
│         │                 │            │            │        │
└─────────┼─────────────────┼────────────┼────────────┼────────┘
          │                 │            │            │
          │ metrics         │ logs       │ queries    │ alerts
          │ scrape          │ collect    │            │
          │                 │            │            │
┌─────────┼─────────────────┼────────────┼────────────┼────────┐
│         ▼                 ▼            ▼            ▼        │
│              Email Service (email-service)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ API Container (email-api)                            │   │
│  │ - Prometheus /metrics endpoint (:8010/metrics)       │   │
│  │ - Structured JSON logging                            │   │
│  │ - Docker labels for service discovery                │   │
│  │ - Connected to activity-observability network        │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Worker Containers (email-worker x3)                  │   │
│  │ - Structured JSON logging                            │   │
│  │ - Docker labels for log collection                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Implementation Components

### 1. Metrics Module (`metrics.py`)

Created comprehensive Prometheus metrics covering all critical business operations.

#### Email Delivery Metrics
- `email_service_emails_total` - Counter tracking all email processing by status, priority, provider
- `email_service_delivery_duration_seconds` - Histogram of full email delivery lifecycle
- `email_service_send_duration_seconds` - Histogram of SMTP/API send operations only
- `email_service_email_size_bytes` - Histogram of email message sizes

#### Queue Metrics
- `email_service_queue_depth` - Gauge of current queue sizes by priority
- `email_service_queue_operations_total` - Counter of queue operations (enqueue/dequeue/retry)
- `email_service_queue_wait_duration_seconds` - Histogram of queue wait times
- `email_service_dlq_size` - Gauge of Dead Letter Queue size

#### Provider Metrics
- `email_service_provider_available` - Gauge of provider health status
- `email_service_provider_response_seconds` - Summary of provider API response times
- `email_service_provider_errors_total` - Counter of provider errors with retriability
- `email_service_provider_rate_limit_hits_total` - Counter of rate limit encounters
- `email_service_provider_connections` - Gauge of connection pool status

#### Worker Metrics
- `email_service_workers_active` - Gauge of active worker count
- `email_service_worker_status` - Gauge of worker health per worker ID
- `email_service_worker_tasks_total` - Counter of tasks processed per worker
- `email_service_worker_processing_seconds` - Histogram of worker processing time
- `email_service_worker_restarts_total` - Counter of worker restarts

#### Redis Metrics
- `email_service_redis_connected` - Gauge of Redis connection status
- `email_service_redis_operations_total` - Counter of Redis operations
- `email_service_redis_operation_duration_seconds` - Histogram of Redis operation latency
- `email_service_redis_pool_connections` - Gauge of connection pool stats

#### HTTP Metrics (Automatic)
Provided by `prometheus-fastapi-instrumentator`:
- `http_requests_total` - Counter of HTTP requests by method, status
- `http_request_duration_seconds` - Histogram of request duration
- `http_requests_inprogress` - Gauge of concurrent requests
- `http_request_size_bytes` - Summary of request sizes
- `http_response_size_bytes` - Summary of response sizes

### 2. API Integration (`api.py`)

#### Prometheus Instrumentator
```python
instrumentator = Instrumentator(
    should_group_status_codes=False,  # Track exact status codes
    should_ignore_untemplated=True,   # Ignore unknown endpoints
    should_respect_env_var=True,      # Respect ENABLE_METRICS env var
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app)
```

#### Metrics Endpoint (`/metrics`)
- Exposes Prometheus metrics in text format
- Updates queue depth gauges before exposure
- Returns proper Content-Type: `text/plain; version=0.0.4`
- No authentication required (designed for internal scraping)

#### Business Metrics Tracking
Email send operations automatically track:
```python
metrics.emails_total.labels(
    status="queued",
    priority=request.priority.value,
    provider=request.provider.value
).inc(recipient_count)

metrics.queue_operations_total.labels(
    operation="enqueue",
    queue=request.priority.value,
    status="success"
).inc()
```

### 3. Docker Configuration

#### Docker Compose Labels
```yaml
labels:
  # Prometheus metrics scraping
  - "prometheus.scrape=true"
  - "prometheus.port=8010"
  - "prometheus.path=/metrics"
  # Loki log collection
  - "loki.collect=true"
  # Service metadata
  - "service.name=email-api"
  - "service.type=api"
  - "service.team=platform"
```

#### Logging Configuration
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service.name,service.type"
```

#### Network Configuration
```yaml
networks:
  - email_network           # Internal service communication
  - activity-observability  # External observability stack
```

#### Environment Variables
```yaml
environment:
  - LOG_FORMAT=json              # Structured logging for Loki
  - ENVIRONMENT=development      # Environment tag for metrics
  - ENABLE_METRICS=true          # Enable Prometheus instrumentation
```

## Metrics Taxonomy

### Labeling Strategy

**Consistent Labels Across Metrics:**
- `priority`: high, medium, low
- `status`: queued, sent, failed, error, success
- `provider`: sendgrid, mailgun, smtp, aws_ses
- `operation`: enqueue, dequeue, retry, send, confirm
- `queue_type`: pending, processing, dlq

### Histogram Buckets

**Email Delivery Duration** (queue → send → confirm):
```
[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0] seconds
```
Covers instant delivery to 5-minute delays.

**Email Send Duration** (SMTP/API call only):
```
[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0] seconds
```
Covers fast API calls to slow SMTP timeouts.

**Queue Wait Duration**:
```
[1, 5, 10, 30, 60, 300, 600, 1800, 3600] seconds
```
Covers immediate processing to 1-hour delays.

**Redis Operation Duration**:
```
[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0] seconds
```
Covers sub-millisecond to slow operations.

## Usage Examples

### Accessing Metrics

**Direct Metrics Endpoint:**
```bash
curl http://localhost:8010/metrics
```

**Health Check:**
```bash
curl http://localhost:8010/health
```

**Sample Metrics Output:**
```
# HELP email_service_emails_total Total number of emails processed
# TYPE email_service_emails_total counter
email_service_emails_total{priority="high",provider="smtp",status="queued"} 42.0
email_service_emails_total{priority="medium",provider="sendgrid",status="sent"} 1523.0

# HELP email_service_queue_depth Current number of emails in queue
# TYPE email_service_queue_depth gauge
email_service_queue_depth{priority="high",queue_type="pending"} 0.0
email_service_queue_depth{priority="medium",queue_type="pending"} 0.0
email_service_queue_depth{priority="low",queue_type="pending"} 0.0

# HELP email_service_redis_connected Redis connection status (1=connected, 0=disconnected)
# TYPE email_service_redis_connected gauge
email_service_redis_connected 1.0
```

### Prometheus Queries

**Email Throughput (rate over 5 minutes):**
```promql
rate(email_service_emails_total[5m])
```

**Email Success Rate:**
```promql
sum(rate(email_service_emails_total{status="sent"}[5m]))
/
sum(rate(email_service_emails_total[5m]))
```

**95th Percentile Email Delivery Duration:**
```promql
histogram_quantile(0.95,
  rate(email_service_delivery_duration_seconds_bucket[5m])
)
```

**Queue Depth by Priority:**
```promql
email_service_queue_depth{queue_type="pending"}
```

**Provider Error Rate:**
```promql
sum by (provider) (
  rate(email_service_provider_errors_total[5m])
)
```

**Worker Health Status:**
```promql
email_service_workers_active > 0
```

**Redis Connection Status:**
```promql
email_service_redis_connected == 1
```

## Verification

### ✅ Successfully Verified

1. **Metrics Endpoint**: http://localhost:8010/metrics returns Prometheus metrics
2. **Health Endpoint**: http://localhost:8010/health returns Redis connection status
3. **Docker Labels**: Properly configured for Prometheus and Loki discovery
4. **Network Connectivity**: email-api connected to activity-observability network
5. **Structured Logging**: JSON format logging configured with rotation
6. **Service Discovery Labels**: prometheus.scrape=true, loki.collect=true set

### ⚠️ Known Issues

**Prometheus Service Discovery:**
The observability-stack's Prometheus container has permission denied errors when accessing the Docker socket:
```
error while listing containers: permission denied while trying to connect to
the Docker daemon socket at unix:///var/run/docker.sock
```

**Resolution**: This is an observability-stack configuration issue (not email-service). The Prometheus container needs:
- Proper Docker socket volume mount with permissions
- OR static scrape configuration as fallback

**Workaround**: Use static Prometheus configuration:
```yaml
scrape_configs:
  - job_name: 'email-service'
    static_configs:
      - targets: ['email-api:8010']
        labels:
          service: 'email-api'
          environment: 'development'
```

## Best Practices Implemented

### RED Method Coverage
- **Rate**: `http_requests_total`, `email_service_emails_total`
- **Errors**: Status code tracking, `email_service_provider_errors_total`
- **Duration**: Request duration histograms, delivery duration histograms

### USE Method Coverage (Resources)
- **Utilization**: Worker active count, connection pool gauges
- **Saturation**: Queue depth, requests in progress
- **Errors**: Provider errors, Redis operation failures

### Four Golden Signals
- **Latency**: Histogram metrics for all operations
- **Traffic**: Counter metrics for all requests
- **Errors**: Status labels and error counters
- **Saturation**: Queue depth and worker capacity gauges

### Cardinality Management
- Limited label values to prevent explosion
- No user IDs or email addresses in labels
- Consistent label naming across metrics
- Proper metric types (Counter/Gauge/Histogram/Summary)

## Future Enhancements

### Recommended Additions

1. **Grafana Dashboards**
   - Email delivery overview dashboard
   - Queue health dashboard
   - Provider performance dashboard
   - Worker pool health dashboard

2. **AlertManager Rules**
   - High error rate alerts
   - Queue backup alerts
   - Provider downtime alerts
   - Worker health alerts
   - Redis connection loss alerts

3. **Distributed Tracing**
   - Add OpenTelemetry for request tracing
   - Trace email journey from API → Queue → Worker → Provider
   - Correlate logs, metrics, and traces

4. **Log Enrichment**
   - Add structured fields: request_id, user_id, job_id
   - Correlate logs with metrics using labels
   - Add trace IDs to logs for correlation

5. **SLI/SLO Definition**
   - Define email delivery SLOs (e.g., 99.9% success rate)
   - Track SLI metrics for SLO compliance
   - Create error budget tracking

## Dependencies

### Python Packages
```
prometheus-client==0.19.0
prometheus-fastapi-instrumentator==6.1.0
```

### External Services
- Prometheus (port 9091)
- Loki (port 3100)
- Grafana (port 3002)
- AlertManager (port 9093)

### Docker Networks
- `activity-observability` (external, created by observability-stack)
- `email_network` (internal)

## Troubleshooting

### Metrics Not Appearing

**Check endpoint:**
```bash
curl http://localhost:8010/metrics
```

**Check Prometheus targets:**
Navigate to http://localhost:9091/targets

**Check Docker labels:**
```bash
docker inspect freeface-email-api | jq '.[0].Config.Labels'
```

### Logs Not Collected

**Check Promtail status:**
```bash
docker logs observability-promtail
```

**Check log format:**
```bash
docker logs freeface-email-api --tail 10
```

**Verify log labels:**
```bash
docker inspect freeface-email-api | jq '.[0].HostConfig.LogConfig'
```

### High Cardinality Issues

**Check metric cardinality:**
```bash
curl -s http://localhost:8010/metrics | grep email_service | wc -l
```

**Identify problematic metrics:**
Look for metrics with many unique label combinations.

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [RED Method](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/)
- [USE Method](http://www.brendangregg.com/usemethod.html)
- [Four Golden Signals](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus FastAPI Instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)

## Conclusion

This implementation provides production-grade observability for the email-service, following industry best practices and standards. The service is now fully instrumented for:

- ✅ Real-time metrics collection
- ✅ Structured log aggregation
- ✅ Service discovery integration
- ✅ Health monitoring
- ✅ Performance tracking
- ✅ Error tracking and alerting readiness

The foundation is in place for comprehensive monitoring, alerting, and operational insights.
