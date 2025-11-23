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

## 📊 Production Monitoring

### `monitor_logs.py` - Real-Time Log Monitor

Monitor bot logs with pattern highlighting for critical issues.

```bash
# Follow logs in real-time
python scripts/monitor_logs.py --follow

# Show only critical issues (panic, unhedged, errors)
python scripts/monitor_logs.py --follow --critical-only

# Show last 100 lines, errors only
python scripts/monitor_logs.py --tail 100 --errors-only
```

**Detects:**
- 🚨 Panic mode triggers
- ⚠️ Unhedged positions
- 🔴 Trade execution failures
- 📡 Repeated API errors
- 💰 Insufficient balance errors

**Use this:**
- During first production runs
- After configuration changes
- When debugging issues

---

### `check_positions.py` - Position Checker

Check for unhedged/orphaned positions and balance discrepancies.

```bash
# One-time check
python scripts/check_positions.py

# Continuous monitoring (check every 5 minutes)
python scripts/check_positions.py --loop 300

# Send alerts if issues detected
python scripts/check_positions.py --loop 300 --alert-on-unhedged
```

**Checks:**
- Internal risk manager state
- Virtual balance availability
- Locked balances with no open arbitrages
- Discrepancies between tracked and real positions

**Critical for:**
- Detecting crashes during trade execution
- Finding orphaned positions
- Balance reconciliation

---

### `export_metrics.py` - Metrics Export

Export bot metrics for offline analysis.

```bash
# Print summary to terminal
python scripts/export_metrics.py

# Export to JSON
python scripts/export_metrics.py --format json --output metrics.json

# Export to CSV
python scripts/export_metrics.py --format csv --output metrics.csv
```

**Exports:**
- Prometheus metrics (trades, PnL, opportunities)
- Balance state (available, locked, used)
- Risk state (exposure, open arbitrages, panic mode)
- Recent statistics from opportunities.csv

**Use for:**
- Performance analysis
- Balance tracking over time
- Incident investigation
- Reporting

---

### `validate_events.py` - Event Validation

**CRITICAL**: Validate that events on different exchanges refer to the SAME real-world occurrence.

```bash
python scripts/validate_events.py \
  --pm-event "Trump wins 2024 election" \
  --pm-desc "Resolves YES if Trump wins..." \
  --sx-event "Trump 2024 winner" \
  --sx-desc "Resolves to YES if Donald Trump..." \
  --strict
```

**Why this matters:**
- Prevents arbitrage between DIFFERENT events
- Different events = guaranteed loss, not profit
- Uses Perplexity AI for semantic comparison

**When to use:**
- BEFORE enabling real trading on new market pairs
- When market descriptions are ambiguous
- If resolution criteria differ across exchanges

**Requirements:**
- `PERPLEXITY_API_KEY` in .env
- Or `ALLOW_UNVALIDATED_EVENTS=true` (NOT recommended)

---

### Future scripts (TODO)

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
