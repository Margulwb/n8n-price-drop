# Price Drop Tracker

A real-time ETF price monitoring application deployed on Kubernetes (Minikube). It tracks daily price changes for a set of ETFs using Yahoo Finance data and sends multi-level Telegram alerts when prices drop beyond configured thresholds.

## Features

- **Multi-level alerts** — first alert at **-1.0%**, then every additional **-0.5%** drop (-1.5%, -2.0%, -2.5%, …)
- **Daily threshold reset** — alert thresholds reset automatically at midnight
- **Friendly ETF names** — human-readable names in alerts, logs, and the web UI
- **Market hours aware** — price checks run only between 09:00–18:00
- **Telegram notifications** — automatic alerts + manual "Send to Telegram" button
- **Web dashboard** — real-time price overview with auto-refresh
- **Persistent storage** — logs and alert state survive pod restarts via `hostPath` volumes
- **Non-root container** — runs as `appuser` (UID 1000) for security
- **CI/CD** — GitHub Actions runs pytest tests on every push

## Tracked Symbols

| Symbol | Name |
|---|---|
| ISAC.L | MSCI ACWI Global |
| CNDX.L | NASDAQ 100 |
| CSPX.L | S&P 500 |
| FLXC.DE | FTSE China |
| VWCG.DE | FTSE Developed Europe |
| ETFBW20TR.WA | WIG20 |
| FLXI.DE | FTSE India |
| VVSM.DE | Semiconductor |

## Architecture

```
┌────────────────┐      ┌───────────────────────┐      ┌──────────────┐
│  Yahoo Finance │◄─────│   Flask App (gunicorn)│─────►│ Telegram Bot │
│  API           │      │   + APScheduler       │      │ API          │
└────────────────┘      └─────────┬─────────────┘      └──────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              ┌─────▼─────┐ ┌────▼────┐  ┌─────▼─────┐
              │ /var/log/ │ │ /opt/   │  │ Web UI    │
              │ price-drop│ │ price-  │  │ :5000     │
              │ (logs)    │ │ drop    │  │           │
              └───────────┘ │ (state) │  └───────────┘
                            └─────────┘
```

- **Flask + gunicorn** — serves the web UI and API (2 workers, port 5000)
- **APScheduler** — runs `check_prices()` every `CHECK_INTERVAL` seconds (default: 90s)
- **hostPath volumes** — persist logs (`/var/log/price-drop`) and alert thresholds (`/opt/price-drop`) on the Minikube host

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- A Telegram Bot token and chat ID

## Quick Start

### 1. Install Docker, kubectl & Minikube

Run the provided script — it installs Docker, kubectl, Minikube, starts the cluster, and sets up hostPath permissions:

```bash
./install-minikube.sh
```

> **Note:** After running the script, log out and back in for the `docker` group to take effect.

### 2. Create Kubernetes Secret

Create `price-drop/kubernetes/secret.yaml` with your Telegram credentials:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: price-drop-secrets
type: Opaque
data:
  chat-id: <base64-encoded-chat-id>
  token: <base64-encoded-token>
```

Apply it:

```bash
kubectl apply -f price-drop/kubernetes/secret.yaml
```

### 3. Deploy

```bash
./deploy-price-drop.sh
```

This script will:
1. Build the Docker image with a timestamp tag
2. Push it to Docker Hub (`margulewicz/price-drop:<timestamp>`)
3. Update the image tag in `deployment.yaml`
4. Apply the Kubernetes manifest
5. Restart the deployment and wait for rollout

### 4. Access the Application

Port-forward the service:

```bash
kubectl port-forward svc/price-drop-svc 8080:80
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

A convenience script is also available:

```bash
./port-forward.sh
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Web dashboard |
| GET | `/health` | Health check (used by K8s probes) |
| GET | `/status` | Last price check results (JSON) |
| GET | `/symbols` | List of tracked symbols (JSON) |
| GET | `/logs` | Today's log entries (JSON) |
| POST | `/check-prices` | Trigger a manual price check |
| POST | `/send-status-telegram` | Send current status to Telegram |

## Alert Logic

1. Every `CHECK_INTERVAL` seconds (between 09:00–18:00), the app fetches the current price for each symbol from Yahoo Finance.
2. It calculates the daily percentage change from the previous close.
3. If the change drops to **-1.0%** or below, the first Telegram alert is sent.
4. For every additional **-0.5%** drop (e.g., -1.5%, -2.0%, -2.5%), a new alert is sent.
5. Already-sent thresholds are tracked in `/opt/price-drop/alert_thresholds` (JSON) and **reset daily at midnight**.

Example: if a symbol drops from 0% to -2.3% during the day, alerts are sent at -1.0%, -1.5%, and -2.0%.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CHECK_INTERVAL` | `300` | Seconds between price checks |
| `TELEGRAM_CHAT_ID` | — | Telegram chat ID (from K8s Secret) |
| `TELEGRAM_TOKEN` | — | Telegram bot token (from K8s Secret) |

In the Kubernetes deployment, `CHECK_INTERVAL` is set to `90`.

## Project Structure

```
k8s-price-drop/
├── deploy-price-drop.sh          # Build, push & deploy script
├── port-forward.sh               # kubectl port-forward helper
├── .github/
│   └── workflows/
│       └── tests.yml             # GitHub Actions CI pipeline
└── price-drop/
    ├── app.py                    # Main Flask application
    ├── Dockerfile                # Container image (non-root)
    ├── requirements.txt          # Python dependencies
    ├── docker-compose.yaml       # Local development
    ├── templates/
    │   └── index.html            # Web dashboard
    ├── src/
    │   ├── file/
    │   │   ├── check_alert_send.py   # Alert threshold storage (JSON)
    │   │   └── logs.py               # File-based logging
    │   └── telegram/
    │       └── send.py               # Telegram Bot API client
    ├── kubernetes/
    │   ├── deployment.yaml       # Deployment + Service manifest
    │   └── secret.yaml           # Telegram credentials
    └── tests/
        └── test_app.py           # 33 pytest tests
```

## Testing

Run tests locally:

```bash
cd price-drop
pip install -r requirements.txt
pip install pytest pytest-cov

# Create required directories
sudo mkdir -p /var/log/price-drop /opt/price-drop
sudo chmod 777 /var/log/price-drop /opt/price-drop

# Run tests
TELEGRAM_CHAT_ID=test TELEGRAM_TOKEN=test pytest tests/ -v --tb=short --cov=. --cov-report=term-missing
```

Tests also run automatically via GitHub Actions on every push to `main` or `feature/*` branches.

## Kubernetes Details

- **Deployment**: 1 replica, resource limits (500m CPU / 256Mi memory)
- **Probes**: liveness (`/health`, period 10s) and readiness (`/health`, period 5s)
- **Init container**: `wait-for-dns` — ensures DNS resolution is available before the app starts
- **Service**: `ClusterIP` on port 80, forwarding to container port 5000
- **Volumes**: `hostPath` for persistent logs and alert state

## Tech Stack

- **Python 3.12** / Flask 3.0 / gunicorn 21.2
- **APScheduler** — background job scheduling
- **Yahoo Finance API** — real-time ETF price data
- **Telegram Bot API** — alert notifications
- **Docker** — containerization with non-root user
- **Kubernetes (Minikube)** — orchestration
- **pytest** — testing (33 tests with coverage)
- **GitHub Actions** — CI pipeline
