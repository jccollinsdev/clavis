# Uptime Monitoring

Use UptimeRobot on the free tier against the backend health endpoint:

- Monitor type: `HTTP(s)`
- URL: `https://clavis.andoverdigital.com/health`
- Method: `GET`
- Check interval: `5 minutes`
- Expected status: `200`
- Expected body: `{"status":"ok"}`

Recommended setup:

1. Create a monitor for the `/health` endpoint.
2. Name it `Clavis API Health`.
3. Set the alert contact to your primary inbox.
4. Add a second check for the MiroFish service if you want dependency visibility.

Notes:

- The backend already exposes `/health`.
- Keep the alert channel simple until launch.
