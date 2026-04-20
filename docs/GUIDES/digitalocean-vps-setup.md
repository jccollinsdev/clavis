# DigitalOcean VPS Setup

This runbook sets up Clavis on a single DigitalOcean droplet with two Docker containers:

- `backend` (FastAPI)
- `mirofish` (local analysis sidecar)

The public endpoint stays behind the existing Cloudflare Tunnel.

Production deploys are driven from `main` via GitHub Actions. `develop` stays for local integration work.

## Recommended Purchase

- Plan: basic droplet
- CPU/RAM: 2 GB RAM is workable, 4 GB is safer for long analysis runs
- Disk: 40-50 GB SSD
- OS: Ubuntu 24.04 LTS
- Auth: SSH key only

## Before You Buy

1. Confirm the Cloudflare tunnel name you want to keep using, currently `clavis-prod`.
2. Make sure you can copy these secrets to the VPS later:
   - `backend/.env`
   - `backend/apns/apns.p8`
   - Cloudflare tunnel credentials or token
3. Decide the VPS hostname, for example `clavis-prod`.

## VPS Bootstrap

Log in as root, then run:

```bash
apt update
apt install -y ca-certificates curl git ufw
adduser clavis
usermod -aG sudo clavis
ufw allow OpenSSH
ufw enable
```

Install Docker and the compose plugin:

```bash
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
usermod -aG docker clavis
```

Reconnect as `clavis` so the sudo and docker group memberships apply.

## Deploy Location

The deploy target is `/opt/clavis`. GitHub Actions syncs the `main` branch there automatically.

Create the directory once:

```bash
mkdir -p /opt/clavis/backend/apns
```

## Copy Secrets

Place the backend env file and APNs key on the VPS:

```bash
mkdir -p /opt/clavis/backend/apns
cp /path/to/backend.env /opt/clavis/backend/.env
cp /path/to/apns.p8 /opt/clavis/backend/apns/apns.p8
chmod 600 /opt/clavis/backend/.env /opt/clavis/backend/apns/apns.p8
```

Do not commit those files.

## Start The Stack

```bash
cd /opt/clavis
docker compose up -d --build
docker compose ps
```

Verify locally on the VPS:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/health
```

## Cloudflare Tunnel

Use your existing `clavis-prod` tunnel credentials or token.

Install `cloudflared` on the VPS:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
dpkg -i /tmp/cloudflared.deb
```

If you have a credentials file, place it under `/etc/cloudflared/` and run the tunnel as a systemd service.

Example service file:

```ini
[Unit]
Description=Cloudflare Tunnel for Clavis
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/cloudflared tunnel run clavis-prod
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
systemctl daemon-reload
systemctl enable --now cloudflared
systemctl status cloudflared
```

## Verify

1. Open `https://clavis.andoverdigital.com/health`
2. Confirm the backend logs show scheduler startup
3. Confirm `docker compose ps` shows both containers healthy
4. Confirm UptimeRobot still checks `/health`
5. Confirm the `main` branch deploy workflow completes successfully after a test push

## Day-2 Operations

- Update code locally, merge to `main`, and let GitHub Actions sync the droplet
- Rebuild manually with `docker compose up -d --build` only when debugging on the VPS
- Check logs with `docker logs clavis-backend-1`
- Restart only the backend with `docker restart clavis-backend-1`

## Notes

- Keep port 8000 and 8001 closed to the public Internet.
- The tunnel should be the only public entry point.
- Store all API keys only on the VPS.
