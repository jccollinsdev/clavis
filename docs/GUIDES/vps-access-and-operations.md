# VPS Access And Operations

This guide explains how Clavis is accessed on the live VPS and how to operate it safely.

## Live VPS

- IP: `134.122.114.241`
- SSH user: `clavix-backend`
- SSH key: `~/.ssh/clavix_vps_ed25519`
- Deploy path: `/opt/clavis`
- Public URL: `https://clavis.andoverdigital.com`

## SSH Access

Use the SSH key, not a password, for normal access:

```bash
ssh -i ~/.ssh/clavix_vps_ed25519 clavix-backend@134.122.114.241
```

If you need to work as root, use `sudo` on the VPS after logging in as `clavix-backend`.

## What Runs There

The VPS runs:

- `clavis-backend-1` - FastAPI backend
- `clavis-mirofish-1` - analysis sidecar
- `cloudflared` - tunnels the public hostname to the VPS

## Main Commands

From the VPS:

```bash
cd /opt/clavis
docker compose up -d --build
docker compose ps
docker logs clavis-backend-1
docker restart clavis-backend-1
```

## Updating Secrets

Secrets live only in `/opt/clavis/backend/.env` on the VPS.

Examples:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `MINIMAX_API_KEY`
- `APNS_KEY_ID`
- `APNS_TEAM_ID`
- `APNS_KEY_PATH`
- `ADMIN_PASSWORD`

Do not commit that file.

## Admin Dashboard

Open:

```text
https://clavis.andoverdigital.com/admin
```

Login with the admin password configured in `backend/.env`.

After login, the dashboard can:

- show backend and scheduler status
- show recent users and runs
- trigger digest, metadata refresh, structural refresh, and S&P backfill actions

## Common Operations

### Restart backend after code changes

```bash
cd /opt/clavis
docker compose up -d --build backend
```

### Check live health

```bash
curl https://clavis.andoverdigital.com/health
```

### Check admin login

```bash
curl -s -X POST https://clavis.andoverdigital.com/admin/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"<admin-password>"}'
```

### Verify the stack

```bash
docker compose ps
```

## Safety Notes

- Keep port `8000` and `8001` private.
- Use the Cloudflare tunnel as the only public entry point.
- Never place secrets in tracked files.
- Prefer small targeted restarts over full VM changes.
