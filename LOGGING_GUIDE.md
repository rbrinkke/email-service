# 📋 FreeFace Email Service - Logging Configuration Guide

## Overzicht van Wijzigingen

Deze implementatie voorziet de FreeFace Email Service van een **professionele, Docker-native logging architectuur** volgens de best practices uit het architecturale rapport.

### ✅ Wat is er geïmplementeerd?

**Fase 1: Clean Logging naar STDOUT/STDERR** ✓
- Alle logs gaan nu naar Docker stdout/stderr (geen lokale bestanden meer)
- File handlers volledig verwijderd uit alle componenten
- Docker logs werken nu perfect: `docker logs freeface-email-api`

**Fase 2: Granulaire Controle via dictConfig** ✓
- Centrale logging configuratie in `config/logging_config.py`
- YAML-based configuratie voor flexibele aanpassingen
- Per-logger niveau controle (applicatie vs third-party)
- Third-party noise filtering (redis, asyncio blijven op WARNING)
- Duplicate log preventie door propagatie management

### 🎯 Belangrijkste Voordelen

1. **Debug Modus Direct Beschikbaar**
   - `LOG_LEVEL=DEBUG` in `.env` → Volledige debug output
   - `LOG_LEVEL=INFO` in productie → Minimale ruis

2. **Granulaire Controle**
   - Application loggers op DEBUG tonen alles
   - Third-party libraries (redis, asyncio) blijven op WARNING
   - Voorkomt log explosie en bespaart kosten

3. **Docker-Native**
   - Alle logs via `docker logs` commando
   - Werkt perfect met log aggregators (ELK, CloudWatch, Loki)
   - Geen volume mounts meer nodig

4. **Environment-Aware**
   - Development: DEBUG logging standaard
   - Production: INFO/WARNING voor kostenefficiëntie
   - Eenvoudig te switchen via environment variables

---

## 📚 Quick Start

### 1. Lokaal Testen (zonder Docker)

```bash
# Test de logging configuratie
python test_logging_config.py

# Verwachte output: ✅ ALL TESTS PASSED
```

### 2. Docker Containers Rebuilden

```bash
# Stop bestaande containers
docker-compose down

# Rebuild met nieuwe logging configuratie
docker-compose build

# Start services
docker-compose up
```

### 3. Logs Bekijken

```bash
# Alle services
docker-compose logs -f

# Specifieke service
docker logs -f freeface-email-api

# Laatste 100 regels
docker logs freeface-email-worker-1 --tail 100

# Volg alleen errors (stderr)
docker logs freeface-email-api 2>&1 | grep ERROR
```

---

## ⚙️ Configuratie

### Environment Variables (.env)

```bash
# ============================================================
# LOGGING CONFIGURATIE
# ============================================================

# Globaal log level
# Opties: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=DEBUG          # Development
# LOG_LEVEL=INFO         # Production

# Environment identifier
ENVIRONMENT=development   # of staging, production

# Log format (toekomstige JSON ondersteuning)
LOG_FORMAT=text          # of json (Fase 4)

# ============================================================
# GEAVANCEERDE CONTROLE (Optioneel)
# ============================================================

# Override specifieke loggers
# LOGGER_LEVEL_REDIS=DEBUG              # Redis debug logs
# LOGGER_LEVEL_UVICORN_ERROR=DEBUG      # Uvicorn server debug
# LOGGER_LEVEL_PROVIDERS=DEBUG          # Email provider debug
```

### YAML Configuratie (config/logging.yaml)

De granulaire controle zit in `config/logging.yaml`:

```yaml
loggers:
  # Application loggers (DEBUG in development)
  email_system:
    level: DEBUG
  api:
    level: DEBUG
  worker:
    level: DEBUG

  # Third-party loggers (WARNING to reduce noise)
  redis:
    level: WARNING
  asyncio:
    level: WARNING
  httpx:
    level: WARNING
```

---

## 🔧 Gebruik Scenarios

### Scenario 1: Normale Development (veel debug info)

```bash
# In .env
LOG_LEVEL=DEBUG
ENVIRONMENT=development

docker-compose up

# Resultaat: Volledige debug output van applicatie
# Third-party libraries blijven stil (WARNING level)
```

**Voorbeeld output:**
```
2025-11-08 10:43:43 - [email_system] - DEBUG - Processing email job abc123
2025-11-08 10:43:43 - [api] - DEBUG - Request received: POST /send
2025-11-08 10:43:43 - [worker] - DEBUG - Worker worker-1 processing queue
```

---

### Scenario 2: Production (minimale ruis)

```bash
# In .env
LOG_LEVEL=INFO
ENVIRONMENT=production

docker-compose up

# Resultaat: Alleen belangrijke events
# Geen debug noise, veel lager log volume
```

**Voorbeeld output:**
```
2025-11-08 10:43:43 - [email_system] - INFO - Email sent successfully
2025-11-08 10:43:43 - [api] - INFO - Email API service started
2025-11-08 10:43:43 - [worker] - INFO - Email worker worker-1 started
```

---

### Scenario 3: Debug Specifiek Component

Probleem met Redis connectie? Debug alleen Redis:

```bash
# In .env
LOG_LEVEL=INFO                    # Globaal op INFO
LOGGER_LEVEL_REDIS=DEBUG          # Alleen Redis op DEBUG

docker-compose up

# Resultaat: Alleen Redis debug logs, rest blijft INFO
```

**Voorbeeld output:**
```
2025-11-08 10:43:43 - [api] - INFO - Email API service started
2025-11-08 10:43:43 - [redis] - DEBUG - Connected to redis://redis-email:6379
2025-11-08 10:43:43 - [redis] - DEBUG - Executing: GET email:job:123
```

---

### Scenario 4: Troubleshoot Email Provider

Probleem met SMTP? Debug de provider:

```bash
# In .env
LOGGER_LEVEL_PROVIDERS_SMTP_PROVIDER=DEBUG

docker-compose up
docker logs -f freeface-email-worker-1

# Resultaat: Gedetailleerde SMTP communicatie logs
```

---

## 📊 Log Levels Uitleg

| Level | Wanneer Gebruiken | Voorbeeld Use Case |
|-------|-------------------|-------------------|
| **DEBUG** | Development, troubleshooting | "Processing job X", "Redis GET key Y" |
| **INFO** | Production, normal operations | "Service started", "Email sent" |
| **WARNING** | Potentiële problemen | "Rate limit approaching", "Slow query" |
| **ERROR** | Recoverable errors | "Email send failed, retrying" |
| **CRITICAL** | Service failures | "Cannot connect to Redis" |

---

## 🎓 Best Practices

### ✅ DO's

1. **Use DEBUG in Development**
   ```bash
   LOG_LEVEL=DEBUG  # Zie alles, catch issues early
   ```

2. **Use INFO in Production**
   ```bash
   LOG_LEVEL=INFO  # Balans tussen visibility en kosten
   ```

3. **Override Specifieke Loggers voor Troubleshooting**
   ```bash
   LOGGER_LEVEL_REDIS=DEBUG  # Tijdelijk, voor debugging
   ```

4. **Gebruik docker logs voor Realtime Monitoring**
   ```bash
   docker logs -f freeface-email-api
   ```

5. **Filter op Log Level**
   ```bash
   docker logs freeface-email-api 2>&1 | grep ERROR
   docker logs freeface-email-api 2>&1 | grep WARNING
   ```

### ❌ DON'Ts

1. **Niet permanent DEBUG in Production**
   - Log volume explosie
   - Hoge kosten bij cloud logging
   - Performance impact

2. **Geen Hardcoded Log Levels in Code**
   - Gebruik environment variables
   - Flexibel per environment

3. **Niet alle Third-Party Loggers op DEBUG**
   - redis op DEBUG = log explosie
   - Gebruik granulaire overrides

---

## 🧪 Testing & Validatie

### Pre-Deployment Test

```bash
# 1. Run configuration test
python test_logging_config.py

# Verwacht: ✅ ALL TESTS PASSED

# 2. Rebuild containers
docker-compose build

# 3. Start één service ter test
docker-compose up email-api

# 4. Check logs
docker logs freeface-email-api

# Verwacht output:
# - "Logging configured - Environment: development, Level: DEBUG"
# - "Email API service started"
# - Geen errors over missing files of handlers
```

### Validatie Checklist

- [ ] `docker logs` toont alle logs
- [ ] DEBUG level toont application debug logs
- [ ] Third-party logs (redis) niet zichtbaar op DEBUG (alleen WARNING+)
- [ ] Geen errors over `/app/logs/` missing
- [ ] Environment toont correct in logs
- [ ] `LOG_LEVEL=INFO` verbergt DEBUG logs

---

## 🔍 Troubleshooting

### Probleem: Geen logs zichtbaar in Docker

**Symptoom:**
```bash
docker logs freeface-email-api
# Geen output
```

**Oplossing:**
1. Check of container draait:
   ```bash
   docker ps | grep email-api
   ```

2. Check logs van container startup:
   ```bash
   docker-compose logs email-api
   ```

3. Rebuild container:
   ```bash
   docker-compose build email-api
   docker-compose up email-api
   ```

---

### Probleem: DEBUG logs niet zichtbaar

**Symptoom:**
```bash
# LOG_LEVEL=DEBUG in .env
# Maar geen debug logs zichtbaar
```

**Oplossing:**
1. Verify environment variable:
   ```bash
   docker-compose config | grep LOG_LEVEL
   ```

2. Check of .env file wordt geladen:
   ```bash
   docker-compose --env-file .env config
   ```

3. Rebuild containers (environment vars worden tijdens build gelezen):
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up
   ```

---

### Probleem: Te veel third-party noise

**Symptoom:**
```bash
# LOG_LEVEL=DEBUG toont duizenden redis/asyncio logs
```

**Oplossing:**

Dit is normaal gedrag! De YAML config voorkomt dit:

1. Verify YAML wordt geladen:
   ```bash
   python test_logging_config.py
   ```

2. Check YAML config:
   ```bash
   cat config/logging.yaml | grep -A 3 "redis:"
   # Moet level: WARNING tonen
   ```

3. Als het nog steeds gebeurt, check of PyYAML is geïnstalleerd:
   ```bash
   docker-compose exec email-api pip list | grep PyYAML
   ```

---

### Probleem: Logs naar files in plaats van stdout

**Symptoom:**
```bash
# Error: cannot write to /app/logs/api.log
```

**Oplossing:**

Dit zou niet moeten gebeuren na onze wijzigingen. Als het wel gebeurt:

1. Verify code changes:
   ```bash
   grep "FileHandler" api.py worker.py
   # Moet GEEN resultaten tonen
   ```

2. Verify import:
   ```bash
   grep "setup_logging" api.py
   # Moet setup_logging() import tonen
   ```

3. Rebuild:
   ```bash
   docker-compose build --no-cache
   docker-compose up
   ```

---

## 📈 Performance & Kosten

### Log Volume Schatting

**DEBUG Level (Development):**
- ~500-1000 log lines per minuut per worker
- ~30 MB/dag per service (text format)
- Totaal stack: ~150 MB/dag

**INFO Level (Production):**
- ~50-100 log lines per minuut per worker
- ~3 MB/dag per service
- Totaal stack: ~15 MB/dag
- **90% reductie vs DEBUG**

### Cloud Logging Kosten (schatting)

Bij gebruik van CloudWatch/Stackdriver:

| Environment | Volume/maand | Kosten (schatting) |
|-------------|--------------|-------------------|
| Development (DEBUG) | ~4.5 GB | ~$2-3/maand |
| Production (INFO) | ~450 MB | ~$0.20-0.30/maand |

**Besparing door granulaire filtering: 90%**

---

## 🚀 Next Steps (Toekomstige Fases)

Deze implementatie heeft **Fase 1 & 2** afgerond. De volgende fases zijn beschikbaar:

### Fase 3: Context & Tracing (Request/Worker Correlatie)

Voegt toe:
- Request ID tracking in alle logs
- Worker ID in elke log regel
- Correlatie tussen API calls en worker processing

**Wanneer implementeren:** Als je logs wilt correleren tussen services

---

### Fase 4: Structured Logging (JSON Output)

Voegt toe:
- JSON formatted logs voor machine parsing
- Direct compatible met ELK, Loki, CloudWatch
- Structured fields voor filtering

**Wanneer implementeren:** Bij overstap naar log aggregatie platform

---

### Fase 5: Production Hardening

Voegt toe:
- Log sampling (reduce volume in productie)
- Performance metrics logging
- Security event tracking

**Wanneer implementeren:** Voor enterprise productie deployment

---

## 📞 Support & Vragen

**Configuratie Problemen:**
1. Run `python test_logging_config.py`
2. Check output voor specifieke foutmeldingen
3. Verify `.env` file bevat correcte variabelen

**Docker Logging Problemen:**
1. `docker-compose logs` voor alle services
2. `docker logs <container>` voor specifieke service
3. Rebuild containers: `docker-compose build --no-cache`

**Performance Concerns:**
1. Start met INFO level in productie
2. Enable DEBUG alleen voor troubleshooting
3. Use granulaire overrides voor specifieke components

---

## 📝 Changelog

**2025-11-08 - Initial Implementation (Fase 1 & 2)**

✅ Implemented:
- Centralized logging configuration (`config/logging_config.py`)
- YAML-based granular control (`config/logging.yaml`)
- Docker stdout/stderr logging (no file handlers)
- Environment variable support (LOG_LEVEL, ENVIRONMENT)
- Third-party noise filtering (redis, asyncio → WARNING)
- Per-logger level control
- Duplicate log prevention
- Comprehensive test suite (`test_logging_config.py`)

🎯 Results:
- 6/6 tests passing
- DEBUG mode fully functional
- Production-ready INFO level
- ~90% log volume reduction vs unfiltered DEBUG

---

*Voor architecturale details en theoretische achtergrond, zie het originele rapport.*
