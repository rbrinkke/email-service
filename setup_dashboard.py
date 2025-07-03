# File: setup_dashboard.py
# Setup script to create dashboard template file

import os

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FreeFace Email System Monitor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-title {
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-value.high { color: #e74c3c; }
        .stat-value.medium { color: #f39c12; }
        .stat-value.low { color: #27ae60; }
        .queue-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .queue-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .queue-card.high {
            border-top: 4px solid #e74c3c;
        }
        .queue-card.medium {
            border-top: 4px solid #f39c12;
        }
        .queue-card.low {
            border-top: 4px solid #27ae60;
        }
        .rate-limit-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .rate-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .provider-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .rate-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 5px 0;
        }
        .rate-fill {
            height: 100%;
            background: linear-gradient(90deg, #27ae60, #f39c12, #e74c3c);
            transition: width 0.3s ease;
        }
        .last-updated {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-healthy { background: #27ae60; }
        .status-warning { background: #f39c12; }
        .status-critical { background: #e74c3c; }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setInterval(() => {
            location.reload();
        }, 30000);
    </script>
</head>
<body>
    <div class="header">
        <h1>🚀 FreeFace Email System Monitor</h1>
        <div>
            <span class="status-indicator status-healthy"></span>
            System Operational
        </div>
    </div>

    <!-- Main Statistics -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-title">Total Queued</div>
            <div class="stat-value">{{ data.total_queued }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Sent Today</div>
            <div class="stat-value low">{{ data.sent_today }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Failed Today</div>
            <div class="stat-value {% if data.failed_today > 0 %}high{% else %}low{% endif %}">{{ data.failed_today }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Success Rate</div>
            <div class="stat-value">{{ data.success_rate }}</div>
        </div>
    </div>

    <!-- Queue Status -->
    <h2>📮 Queue Status</h2>
    <div class="queue-grid">
        <div class="queue-card high">
            <h3>🚨 HIGH Priority</h3>
            <div class="stat-value high">{{ data.queue_high }}</div>
            <p>Password resets, 2FA codes</p>
        </div>
        <div class="queue-card medium">
            <h3>📧 MEDIUM Priority</h3>
            <div class="stat-value medium">{{ data.queue_medium }}</div>
            <p>Group invites, confirmations</p>
        </div>
        <div class="queue-card low">
            <h3>📰 LOW Priority</h3>
            <div class="stat-value low">{{ data.queue_low }}</div>
            <p>Newsletters, marketing</p>
        </div>
    </div>

    <!-- Rate Limiting Status -->
    <h2>⚡ Rate Limiting Status</h2>
    <div class="rate-limit-grid">
        {% for provider, status in data.rate_status.items() %}
        <div class="rate-card">
            <div class="provider-name">{{ provider.upper() }}</div>
            <div>Tokens: {{ status.tokens }} / {{ status.limit }}</div>
            <div class="rate-bar">
                <div class="rate-fill" style="width: {{ status.utilization if status.utilization != 'N/A' else '0%' }}"></div>
            </div>
            <div>Usage: {{ status.utilization }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="last-updated">
        Last updated: {{ data.last_updated }}
        <br>Auto-refresh every 30 seconds
    </div>
</body>
</html>"""

def setup_dashboard():
    """Create the dashboard template file"""
    # Create templates directory if it doesn't exist
    os.makedirs('/opt/email/templates', exist_ok=True)
    
    # Write the dashboard HTML file
    with open('/opt/email/templates/dashboard.html', 'w') as f:
        f.write(DASHBOARD_HTML)
    
    print("✅ Dashboard template created successfully!")
    print("📁 File: /opt/email/templates/dashboard.html")

if __name__ == "__main__":
    setup_dashboard()
