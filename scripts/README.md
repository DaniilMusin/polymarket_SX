# 🛠️ Production Scripts

This directory contains utility scripts for production deployment and testing.

## 📋 Pre-Deployment Scripts

### `preflight_check.py` - Pre-Flight System Check

Comprehensive validation before starting the bot.

```bash
python scripts/preflight_check.py
```

**Checks:**
- ✓ .env file exists and is valid
- ✓ Private key is configured and loads correctly
- ✓ API keys are set
- ✓ Alert channels configured (Telegram/Discord)
- ✓ Trading parameters are reasonable
- ⚠️ Warnings for unsafe configurations

**Run this BEFORE every deployment!**

---

### `check_balances.py` - Balance Checker

Check your USDC balance on Polygon (for Polymarket).

```bash
python scripts/check_balances.py
```

**Features:**
- Shows USDC balance on Polygon network
- Warns if balance is too low
- Provides wallet address for verification

**Note:** SX and Kalshi require manual checking.

---

## 🧪 Testing Scripts

### `test_run.py` - Safe Test Run

Run bot with conservative test parameters.

```bash
# Simulation mode (no real trades)
python scripts/test_run.py

# Custom parameters
python scripts/test_run.py --position-size 10 --min-profit 100 --duration 300

# REAL TRADING (use with caution!)
python scripts/test_run.py --real --position-size 10
```

**Test Parameters:**
- `MAX_POSITION_SIZE = $10` (customizable)
- `MIN_PROFIT_BPS = 100` (1%)
- `ENABLE_REAL_TRADING = false` (unless --real)
- Auto-stops after 5 minutes (customizable)

**Use this for:**
- Testing configuration
- Validating bot behavior
- First real money test

---

### `test_telegram.py` - Telegram Alert Test

Test your Telegram bot configuration.

```bash
python scripts/test_telegram.py
```

**What it does:**
- Validates `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Sends test message to your Telegram
- Provides setup instructions if not configured

**Setup Telegram:**
1. Create bot: [@BotFather](https://t.me/BotFather)
2. Get chat ID: [@userinfobot](https://t.me/userinfobot)
3. Add to `.env`

---

### `test_discord.py` - Discord Webhook Test

Test your Discord webhook configuration.

```bash
python scripts/test_discord.py
```

**What it does:**
- Validates `DISCORD_WEBHOOK_URL`
- Sends 3 test messages (INFO, WARNING, CRITICAL)
- Shows color coding for different alert levels

**Setup Discord:**
1. Channel Settings → Integrations → Webhooks
2. Create Webhook
3. Copy URL to `.env`

---

## 🚀 Quick Start Workflow

### First Time Setup

```bash
# 1. Run pre-flight check
python scripts/preflight_check.py

# 2. Fix any errors, then check again
python scripts/preflight_check.py

# 3. Test alerts
python scripts/test_telegram.py
python scripts/test_discord.py

# 4. Check balances
python scripts/check_balances.py

# 5. Test run (simulation)
python scripts/test_run.py --duration 60

# 6. If all good, test with real money
python scripts/test_run.py --real --position-size 1 --duration 60
```

### Before Each Deployment

```bash
# Quick validation
python scripts/preflight_check.py && \
python scripts/check_balances.py && \
echo "✅ Ready to deploy!"
```

---

## 📊 Monitoring (TODO)

Future scripts for production monitoring:

- `monitor_logs.py` - Real-time log monitoring with filters
- `check_positions.py` - Check for open/unhedged positions
- `export_metrics.py` - Export metrics to CSV/JSON
- `backup_config.py` - Backup configuration and logs

---

## ⚠️  Important Notes

### Security

- **Never commit `.env` file** (contains private keys!)
- **Backup private key** securely (not in screenshots/cloud)
- **Use strong passwords** for alert channels
- **Rotate API keys** periodically

### Testing

- **Always test in simulation first**
- **Start with small amounts** ($1-10)
- **Increase gradually** after successful runs
- **Monitor constantly** for first 48 hours

### Alerts

- **Set up alerts BEFORE production**
- **Test alerts actually work**
- **Keep alerts enabled on phone**
- **Respond to CRITICAL alerts within minutes**

---

## 🔧 Troubleshooting

### Script won't run

```bash
# Check Python version (need 3.8+)
python --version

# Install dependencies
pip install -r requirements.txt

# Make script executable
chmod +x scripts/*.py
```

### Import errors

```bash
# Make sure you're in project root
cd /path/to/polymarket_SX

# Run from project root
python scripts/preflight_check.py
```

### Permission denied

```bash
# Make scripts executable
chmod +x scripts/*.py

# Run with python explicitly
python scripts/preflight_check.py
```

---

## 📚 Additional Resources

- **Main README**: `../README.md`
- **Production Guide**: `../PRODUCTION_SETUP.md`
- **Example Config**: `../.env.example`

---

**Questions?** Check the main README or create an issue on GitHub.
