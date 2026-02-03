# Railway Deployment Guide

## Prerequisites

1. Railway account: https://railway.app
2. Gmail OAuth token (`token.pickle` file)
3. Environment variables ready

## Deployment Steps

### 1. Prepare token.pickle as Base64

Since `token.pickle` is gitignored and contains credentials, we'll pass it as an environment variable:

```bash
# Convert token.pickle to base64
base64 token.pickle > token.pickle.base64

# Copy the output - you'll paste it as an environment variable
cat token.pickle.base64
```

### 2. Create Railway Project

```bash
# Option A: Using Railway CLI
railway login
railway init
railway up

# Option B: Using Railway Web UI
# 1. Go to https://railway.app/new
# 2. Connect your GitHub repository
# 3. Select the guarantee-email-agent repo
```

### 3. Configure Environment Variables

In Railway dashboard, add these environment variables:

**Required:**
```bash
# Gmail OAuth (from token.pickle.base64)
GMAIL_TOKEN_PICKLE_BASE64=<paste_base64_content_here>

# CRM Abacus API
CRM_ABACUS_USERNAME=your_username
CRM_ABACUS_PASSWORD=your_password

# Gemini AI
GEMINI_API_KEY=your_gemini_key

# Optional: Gmail OAuth Token (fallback if pickle decode fails)
GMAIL_OAUTH_TOKEN=your_token
```

**Optional Configuration:**
```bash
# Admin emails
ADMIN_EMAIL=admin@example.com
SUPERVISOR_EMAIL=supervisor@example.com

# Polling interval (default: 60 seconds)
POLLING_INTERVAL_SECONDS=60
```

### 4. Add Startup Script

Railway will use the `Procfile` which is already configured:
```
worker: uv run python -m guarantee_email_agent run
```

But we need to decode the token.pickle on startup. Let me create a startup script...

### 5. Deploy Settings

**Railway Configuration:**
- **Start Command**: `./scripts/railway-start.sh` (will create this)
- **Build Command**: (Railway auto-detects uv)
- **Worker Type**: Yes (not a web service)
- **Health Check**: Disabled (long-running process)
- **Restart Policy**: Always

### 6. Monitor Deployment

```bash
# Using Railway CLI
railway logs

# Or in Railway dashboard:
# Project > Deployments > View Logs
```

### 7. Verify It's Running

Check logs for:
```
[INFO] Agent starting (restart safe, idempotent)
[INFO] Entering monitoring loop
[INFO] Refreshing Gmail OAuth token from pickle file...
[INFO] Gmail token is still valid
```

## Important Notes

### Token.pickle Handling

Railway doesn't have persistent file storage, so we use base64 environment variable:
1. Token is decoded from env var on startup
2. Written to `/tmp/token.pickle`
3. Token refresh updates `/tmp/token.pickle` (ephemeral, but works for 24h deployments)

### Secrets Management

**DO NOT commit these files:**
- `token.pickle`
- `credentials.json`
- `client_secret_*.json`
- `.env`

They're in `.gitignore` - keep them there!

### Cost Estimate

Railway free tier includes:
- $5 free credit/month
- ~500 hours of runtime
- Enough for 24/7 operation

This agent uses minimal resources:
- Memory: ~100-200 MB
- CPU: Minimal (polling based)
- **Estimated cost**: $0-2/month

### Troubleshooting

**Issue: Token expired errors**
- Railway restarts may lose ephemeral `/tmp/token.pickle`
- Solution: Token auto-refreshes on startup from base64 env var

**Issue: Environment variables not loading**
- Check Railway dashboard > Variables
- Restart deployment after adding variables

**Issue: Logs show "Gmail 401 Unauthorized"**
- Token.pickle base64 may be corrupted
- Regenerate: `base64 token.pickle` and update env var

**Issue: Process exits immediately**
- Check Railway logs for Python errors
- Verify all dependencies in pyproject.toml
- Railway should auto-install with uv

## Alternative: Railway Volumes (Beta)

If Railway volumes are available:
1. Create a volume at `/data`
2. Place `token.pickle` at `/data/token.pickle`
3. Update code to read from `/data/token.pickle`

This provides persistent storage across deployments.

## Scaling

For higher volume:
- Railway Hobby plan: $5/month
- Vertical scaling: Increase memory if needed
- Horizontal scaling: Not needed (single Gmail account)

## CI/CD

Railway auto-deploys on git push:
1. Push to main branch
2. Railway detects change
3. Builds and deploys automatically
4. Zero-downtime deployment

## Health Monitoring

Add Railway cron or external monitoring:
- Check logs for errors
- Monitor Gmail API quota
- Alert on repeated failures

Railway doesn't have built-in health checks for workers, consider:
- **Better Stack** (uptime monitoring)
- **Sentry** (error tracking)
- Railway Webhooks for deployment events
