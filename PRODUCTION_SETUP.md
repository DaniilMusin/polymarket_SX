# 🚀 Production Setup Guide

This guide will help you safely deploy the arbitrage bot to production.

## ⚠️  CRITICAL: Read This First

**This bot trades real money. Mistakes can result in financial loss.**

- Start with **small amounts** ($10-100)
- **Monitor constantly** for the first 48 hours
- Set up **alerts** before going live
- Have a **plan** for manual intervention

---

## 📋 Pre-Flight Checklist

### 1. ✅ Configure Environment Variables

```bash
# Copy example config
cp .env.example .env

# Edit with your values
nano .env  # or use your preferred editor
```

**Required variables:**
```bash
PRIVATE_KEY=<your-eth-private-key>
POLYMARKET_API_KEY=<your-key>
SX_API_KEY=<your-key>
KALSHI_API_KEY=<your-key>
```

**Highly recommended:**
```bash
# Telegram alerts
TELEGRAM_BOT_TOKEN=<from-@BotFather>
TELEGRAM_CHAT_ID=<from-@userinfobot>

# OR Discord alerts
DISCORD_WEBHOOK_URL=<from-channel-settings>
```

**Trading parameters (start conservative):**
```bash
MAX_POSITION_SIZE=10           # Start with $10!
MIN_PROFIT_BPS=100             # 1% minimum profit
ENABLE_REAL_TRADING=false      # Start in simulation mode
```

### 2. ✅ Set Up Alerts (CRITICAL!)

You **MUST** set up at least one alert channel before production.

#### Option A: Telegram Bot

1. Create bot with [@BotFather](https://t.me/BotFather)
   - Send `/newbot`
   - Follow instructions
   - Copy the bot token

2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
   - Send `/start`
   - Copy your chat ID

3. Add to `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
   TELEGRAM_CHAT_ID=123456789
   ```

4. Test it:
   ```bash
   python scripts/test_telegram.py
   ```

#### Option B: Discord Webhook

1. In Discord channel settings:
   - Integrations → Webhooks
   - Create webhook
   - Copy webhook URL

2. Add to `.env`:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

3. Test it:
   ```bash
   python scripts/test_discord.py
   ```

### 3. ✅ Check Balances

```bash
python scripts/check_balances.py
```

**Requirements:**
- Polymarket (Polygon): At least $100 USDC
- SX: Check manually at https://sx.bet/
- Kalshi: Check manually at https://kalshi.com/

### 4. ✅ Run Pre-Flight Check

```bash
python scripts/preflight_check.py
```

This will verify:
- ✓ .env file exists
- ✓ Private key is valid
- ✓ API keys are set
- ✓ Alerts are configured
- ✓ Trading parameters are reasonable

**Fix any errors before continuing!**

### 5. ✅ Backup Private Key

**CRITICAL: Your private key controls your funds!**

```bash
# Print to screen (SECURE LOCATION ONLY!)
grep PRIVATE_KEY .env

# Better: Use a password manager
# 1. Copy private key
# 2. Store in 1Password/LastPass/Bitwarden
# 3. Add recovery contact
```

**Never store in:**
- ❌ Screenshots
- ❌ Cloud storage (Dropbox/Google Drive)
- ❌ Email
- ❌ Slack/Discord messages

### 6. ✅ Test Run (Simulation Mode)

```bash
# Test with simulation (no real trades)
python scripts/test_run.py

# Run for 5 minutes
python scripts/test_run.py --duration 300
```

This runs with:
- `MAX_POSITION_SIZE = $10`
- `MIN_PROFIT_BPS = 100` (1%)
- `ENABLE_REAL_TRADING = false`

**Watch for:**
- ✓ Arbitrage opportunities detected
- ✓ Orders placed successfully (simulated)
- ✓ No errors or crashes
- ✓ Alerts working (if configured)

---

## 🚀 Going Live

### Phase 1: Test with Real Money ($10-100)

**Day 1-7: Validation Phase**

```bash
# Update .env
MAX_POSITION_SIZE=10
MIN_PROFIT_BPS=100
ENABLE_REAL_TRADING=true  # ⚠️  Real money!

# Start bot
python main.py
```

**During this phase:**
- ⏰ Monitor **constantly** (check every 15-30 minutes)
- 📱 Keep alerts enabled on your phone
- 📊 Watch for 🚨 CRITICAL alerts
- 🛑 Be ready to stop bot immediately
- 📝 Log any issues or unexpected behavior

**Stop immediately if:**
- Multiple 🚨 CRITICAL alerts
- Unhedged positions detected
- Unusual behavior
- API errors persist

### Phase 2: Increase Position Size ($50-100)

**Day 8-30: Scaling Phase**

After 7 days of successful operation:

```bash
# Update .env
MAX_POSITION_SIZE=50    # or 100
MIN_PROFIT_BPS=50       # 0.5%
```

**During this phase:**
- ⏰ Monitor regularly (every 1-2 hours)
- 📱 Respond to alerts within 5 minutes
- 📊 Track PnL and success rate
- 🔍 Look for patterns in failed trades

### Phase 3: Production Scale ($500-1000)

**Day 31+: Production Phase**

Only after 30 days of stable operation:

```bash
# Update .env
MAX_POSITION_SIZE=500   # or higher
MIN_PROFIT_BPS=20       # 0.2%
```

**During this phase:**
- ⏰ Automated monitoring
- 📱 Alerts via Telegram/Discord
- 📊 Daily PnL review
- 🔄 Regular balance checks

---

## 📊 Monitoring

### Real-Time Logs

```bash
# Follow logs in real-time
tail -f logs/bot.log | grep --color -E '🚨|ERROR|CRITICAL'
```

### 🚨 CRITICAL Alerts

If you see a CRITICAL alert, it means:

1. **Partial execution detected**
   - One order filled, other failed
   - You have an unhedged position
   - **ACTION: Close position manually IMMEDIATELY**

2. **Example alert:**
   ```
   🚨 CRITICAL: Sell failed but buy succeeded!
   Unhedged position: polymarket order_123 @ 0.45
   Manual intervention required!
   ```

3. **How to respond:**
   - Log into exchange (Polymarket/SX/Kalshi)
   - Find the open position
   - Close it manually at best available price
   - Document the incident

### Metrics Dashboard (Optional)

The bot exposes Prometheus metrics on port 9090:

```bash
# View metrics
curl http://localhost:9090/metrics

# Key metrics:
# - arbitrage_trades_total: Number of trades
# - arbitrage_pnl_total: Total PnL
# - arbitrage_opportunities_found: Opportunities detected
```

Set up Grafana dashboard (optional):
- Import `grafana_dashboard.json` (if provided)
- Connect to localhost:9090
- Monitor in real-time

---

## 🛑 Stopping the Bot

### Graceful Shutdown

```bash
# Press Ctrl+C once
^C

# Wait for message:
# "Shutting down gracefully..."
```

### Emergency Stop

```bash
# Force kill (only if necessary)
pkill -9 -f main.py
```

**After stopping:**
1. Check for any open positions
2. Review logs for errors
3. Verify balances on exchanges

---

## 🔧 Troubleshooting

### Bot won't start

```bash
# Run pre-flight check
python scripts/preflight_check.py

# Check logs
tail -n 100 logs/bot.log
```

### No arbitrage opportunities

This is normal! Arbitrage is rare:
- Check `MIN_PROFIT_BPS` (lower = more opportunities)
- Check orderbook depth (need liquidity)
- Check spreads (must be > fees + slippage)

### Alerts not working

```bash
# Test Telegram
python scripts/test_telegram.py

# Test Discord
python scripts/test_discord.py

# Check .env variables
grep TELEGRAM .env
grep DISCORD .env
```

### Balance too low

```bash
# Check current balance
python scripts/check_balances.py

# Top up:
# - Polymarket: Bridge USDC to Polygon
# - SX: Deposit via their interface
# - Kalshi: Deposit via their interface
```

---

## 📞 Support

### Emergency Contacts

- **Critical bug?** Stop bot immediately, check GitHub issues
- **Need help?** See README.md for contact info
- **Lost funds?** Contact exchange support

### Useful Links

- Polymarket support: https://polymarket.com/support
- SX support: https://docs.sx.bet/
- Kalshi support: https://help.kalshi.com/

---

## ⚖️  Legal Disclaimer

- **Use at your own risk**
- **No guarantees** of profit
- **You are responsible** for your own funds
- **Tax obligations** vary by jurisdiction
- **Regulatory compliance** is your responsibility

---

## 🎯 Success Checklist

Before going live, verify:

- [ ] `.env` configured with real values
- [ ] Private key backed up securely
- [ ] At least one alert channel configured
- [ ] Balances checked on all exchanges
- [ ] Pre-flight check passes
- [ ] Test run completed successfully
- [ ] Started with small position size ($10-100)
- [ ] Monitoring plan in place
- [ ] Response plan for CRITICAL alerts ready
- [ ] Emergency stop procedure understood

**Only proceed if ALL items are checked! ✓**

---

Good luck! 🚀
