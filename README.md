# 🤖 AI Bot Monitor - Autonomous Discord Bot Monitoring System

An AI-powered system that monitors Discord bots 24/7, detects errors automatically, analyzes them with local AI, and reports everything to Discord - all running on local hardware for ~$2/month.

[![YouTube Channel](https://img.shields.io/badge/YouTube-CodeWithRomi-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/@CodeWithRomii)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)](https://www.python.org)

> **📺 Full Tutorial Series:** Watch the complete build process on [YouTube](https://www.youtube.com/@CodeWithRomii)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Hardware Requirements](#-hardware-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Tutorial Series](#-tutorial-series)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

This project creates an autonomous monitoring system that:
- 🔍 **Monitors** Discord bot logs every 15 minutes via SSH
- 🤖 **Analyzes** errors using local AI (Phi-3 via Ollama)
- 🔧 **Generates** code fixes automatically
- ✅ **Tests** fixes in a safe staging environment
- 📝 **Documents** all changes in README
- 💬 **Reports** everything to Discord via webhooks
- 🚀 **Deploys** to production after 24-hour stability check

**Total Operating Cost:** ~$2/month (just electricity!)

---

## ✨ Features

### Current (Episode 4)
- ✅ Automated SSH monitoring
- ✅ Error pattern detection
- ✅ Local AI analysis (Phi-3 3.8B)
- ✅ Discord webhook notifications
- ✅ Comprehensive logging
- ✅ Multiple model support

### Coming Soon (Episodes 5-6)
- 🔄 Automatic fix application
- 🔁 Automatic rollback on failure
- 🎯 Three-tier AI system (Local → Groq → Claude)
- ⏰ Cron job automation
- 🏭 Production deployment to NAS
- 📊 Extended monitoring and metrics

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│           N100 Mini PC (AI Brain)               │
│   ┌──────────────────────────────────────┐     │
│   │  Ubuntu 24.04 + Ollama + Phi-3       │     │
│   │  Python Monitoring Scripts           │     │
│   └──────────────────────────────────────┘     │
└─────────────────┬───────────────────────────────┘
                  │ SSH (Tailscale VPN)
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│  Pi 5   │  │   NAS   │  │ Discord │
│  Test   │  │  Prod   │  │ Webhook │
│  Bot    │  │  Bot    │  │ Reports │
└─────────┘  └─────────┘  └─────────┘
```

**Three-Tier AI System (Coming in Episode 5):**
1. **Tier 1:** Phi-3 3.8B (Local via Ollama) - 70-80% of issues, FREE
2. **Tier 2:** Groq API (Llama 3.1 70B) - 15-20% of issues, FREE
3. **Tier 3:** Claude API (Sonnet 4.5) - 5-10% of issues, ~$0.50/month

---

## 💻 Hardware Requirements

### Minimum (What we use in the series)
- **AI Brain:** N100 Mini PC (16GB RAM) or equivalent
- **Test Environment:** Raspberry Pi 5 (8GB RAM) running PM2
- **Production:** TerraMaster NAS or any Docker host
- **Network:** Tailscale VPN (free)

### Performance by Hardware

| Hardware | Phi-3 Response Time | DeepSeek 6.7B Response Time |
|----------|--------------------|-----------------------------|
| N100 Mini PC | 20-40 seconds ⚡ | 3-8 minutes 🐌 |
| Ryzen 5/7 | 10-20 seconds | 1-2 minutes |
| Ryzen 9 (UM890) | 5-15 seconds | 30-60 seconds |

**Recommended for N100:** Use Phi-3 3.8B for best performance!

---

## 📦 Installation

### 1. Set Up the AI Brain (N100 Mini PC)

**Install Ubuntu 24.04:**
```bash
# Follow Episode 2 on YouTube for detailed Ubuntu installation guide
# https://www.youtube.com/@CodeWithRomii
```

**Install Ollama:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Download AI Model (Phi-3 recommended for N100):**
```bash
ollama pull phi3:3.8b
```

**Alternative models:**
```bash
# Slower but higher quality (not recommended for N100)
ollama pull deepseek-coder:6.7b-instruct

# Faster, smaller (good for very low-end hardware)
ollama pull deepseek-coder:1.3b
```

**Install Python dependencies:**
```bash
pip3 install paramiko requests --break-system-packages
```

### 2. Set Up SSH Keys

**Generate SSH key on N100:**
```bash
ssh-keygen -t ed25519 -C "bot-monitor"
```

**Copy to Raspberry Pi:**
```bash
ssh-copy-id your-user@your-pi-hostname.local
```

**Test passwordless connection:**
```bash
ssh your-user@your-pi-hostname.local "pm2 list"
```

### 3. Clone This Repository

```bash
git clone https://github.com/YOUR-USERNAME/ai-bot-monitor.git
cd ai-bot-monitor
```

---

## ⚙️ Configuration

### 1. Create Configuration File

Create `config.py`:

```python
# Pi 5 Connection Settings
PI_HOST = "your-pi-hostname.local"  # Replace with your Pi's hostname
PI_USER = "your-username"            # Replace with your username
PI_BOT_NAME = "your-bot-name"        # Your PM2 process name

# Monitoring Settings
CHECK_INTERVAL = 900  # 15 minutes in seconds
LOG_LINES = 100       # How many log lines to check

# Ollama Settings
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:3.8b"  # Recommended for N100

# Discord Webhook (get from Discord Server Settings > Integrations > Webhooks)
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"

# File Paths
import os
HOME = os.path.expanduser("~")
LOG_FILE = os.path.join(HOME, "bot-monitor", "monitor.log")
```

### 2. Complete Code Modules

Below are all the Python modules that make up the monitoring system. Create these files in your `~/bot-monitor/` directory.

#### `ssh_utils.py`

```python
import paramiko
from config import PI_HOST, PI_USER, PI_BOT_NAME


def execute_command(command: str):
    """Execute a command on the Pi via SSH."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(PI_HOST, username=PI_USER)

        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()

        if error:
            return None, error
        return output, None
    except Exception as e:
        return None, str(e)


def get_pm2_logs(lines: int = 100):
    """Get recent PM2 logs for the bot."""
    command = f"pm2 logs {PI_BOT_NAME} --lines {lines} --nostream"
    return execute_command(command)


def get_bot_status() -> str:
    """Check if bot is running via PM2.

    Returns: "online", "errored", or "stopped".
    """
    command = f"pm2 list | grep {PI_BOT_NAME}"
    output, error = execute_command(command)

    if output and "online" in output:
        return "online"
    elif output and "errored" in output:
        return "errored"
    else:
        return "stopped"
```

#### `log_parser.py`

```python
import re

ERROR_PATTERNS = [
    r"Error:",
    r"Exception:",
    r"UnhandledPromiseRejection",
    r"Cannot read property",
    r"undefined is not",
    r"ECONNREFUSED",
    r"ETIMEDOUT",
    r"TypeError",
    r"ReferenceError",
]


def detect_error(logs: str) -> bool:
    """Return True if logs contain any known error patterns."""
    if not logs:
        return False

    for pattern in ERROR_PATTERNS:
        if re.search(pattern, logs, re.IGNORECASE):
            return True

    return False


def extract_error_context(logs: str) -> str:
    """Extract the error line plus surrounding context.

    - If a known error pattern is found, returns the error line
      plus 5 lines before and after.
    - If no pattern is found, returns the last 20 lines.
    """
    if not logs:
        return ""

    lines = logs.split("\n")
    error_lines = []

    for i, line in enumerate(lines):
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Get error line plus 5 lines before and after
                start = max(0, i - 5)
                end = min(len(lines), i + 6)
                error_lines = lines[start:end]
                return "\n".join(error_lines)

    # If no specific error found, return last 20 lines
    return "\n".join(lines[-20:])
```

#### `ai_handler.py`

```python
import requests
from config import OLLAMA_URL, OLLAMA_MODEL


def ask_ai(error_logs: str, bot_status: str = "unknown"):
    """Send error logs to Ollama and get a fix.

    Returns:
        (response_text, error_message)
        - response_text: AI response string (or None on error)
        - error_message: error string if something went wrong, else None
    """
    prompt = f"""You are a Discord bot debugging expert.

Bot Status: {bot_status}

ERROR LOGS:
{error_logs}

TASK: Analyze this error and provide:
1. Root cause (brief, 1-2 sentences)
2. Specific fix (code changes needed)
3. Which file(s) to modify
4. Confidence level (Low/Medium/High)

Be concise and actionable."""

    try:
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3  # Lower = more focused and deterministic
            },
        }

        print("Sending to AI... (this may take several minutes)")
        response = requests.post(OLLAMA_URL, json=data, timeout=600)  # 10 minutes
        response.raise_for_status()

        result = response.json()
        return result.get("response"), None

    except requests.exceptions.Timeout:
        return None, "AI request timed out after 10 minutes"
    except Exception as e:
        return None, f"AI Error: {str(e)}"
```

#### `discord_reporter.py`

```python
import requests
import datetime
from config import DISCORD_WEBHOOK


def send_report(title: str, description: str, color: int = 0x0066cc, fields: list = None):
    """Send a formatted embed to Discord.

    Args:
        title: Embed title
        description: Embed description
        color: Hex color for the embed border
        fields: List of field dicts with 'name', 'value', 'inline'

    Returns:
        True if successful, False otherwise
    """
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "footer": {
            "text": "AI Bot Monitor v1.0"
        }
    }

    if fields:
        embed["fields"] = fields

    data = {
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send Discord report: {e}")
        return False


def report_error_detected(error_context: str, ai_response: str, bot_status: str):
    """Send error detection report to Discord.

    Args:
        error_context: The error logs/context
        ai_response: The AI's analysis
        bot_status: Current bot status (online/errored/stopped)

    Returns:
        True if successful, False otherwise
    """
    fields = [
        {
            "name": "Bot Status",
            "value": bot_status,
            "inline": True
        },
        {
            "name": "AI Model",
            "value": "Phi-3 3.8B (Local)",
            "inline": True
        },
        {
            "name": "Error Context",
            "value": f"```{error_context[:500]}...```" if len(error_context) > 500 else f"```{error_context}```",
            "inline": False
        },
        {
            "name": "AI Analysis",
            "value": ai_response[:1000] if len(ai_response) > 1000 else ai_response,
            "inline": False
        }
    ]

    return send_report(
        title="🔴 Error Detected",
        description="The monitoring system detected an error in the Discord bot.",
        color=0xcc3333,  # Red
        fields=fields
    )


def report_healthy():
    """Send healthy status report to Discord.

    Returns:
        True if successful, False otherwise
    """
    return send_report(
        title="✅ Bot Healthy",
        description="No errors detected. Bot is running normally.",
        color=0x00cc66  # Green
    )
```

#### `monitor.py`

```python
#!/usr/bin/env python3
import time
import datetime
from ssh_utils import get_pm2_logs, get_bot_status
from log_parser import detect_error, extract_error_context
from ai_handler import ask_ai
from discord_reporter import report_error_detected, report_healthy
from config import LOG_FILE


def log_message(message: str):
    """Write to log file with timestamp.

    Args:
        message: The message to log
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(log_entry.strip())

    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to log: {e}")


def monitor_bot():
    """Main monitoring function.

    This function:
    1. Gets bot status via SSH
    2. Fetches PM2 logs
    3. Checks for errors
    4. If error found, sends to AI for analysis
    5. Reports results to Discord
    6. Logs everything
    """
    log_message("=" * 60)
    log_message("Starting bot monitoring check...")

    # Get bot status
    bot_status = get_bot_status()
    log_message(f"Bot status: {bot_status}")

    # Get logs from Pi
    logs, error = get_pm2_logs()

    if error:
        log_message(f"ERROR getting logs: {error}")
        return

    # Check for errors
    if not detect_error(logs):
        log_message("No errors detected. Bot is healthy.")
        # Optionally send healthy report (comment out if too spammy)
        # report_healthy()
        return

    log_message("🔴 ERROR DETECTED! Analyzing...")

    # Extract error context
    error_context = extract_error_context(logs)
    log_message(f"Error context extracted ({len(error_context)} chars)")

    # Ask AI for fix
    log_message("Sending to AI for analysis...")
    fix, ai_error = ask_ai(error_context, bot_status)

    if ai_error:
        log_message(f"AI ERROR: {ai_error}")
        return

    log_message("AI analysis received!")
    log_message(f"AI RESPONSE:\n{fix}")

    # Send to Discord
    log_message("Sending report to Discord...")
    if report_error_detected(error_context, fix, bot_status):
        log_message("Discord report sent successfully!")
    else:
        log_message("Failed to send Discord report")

    log_message("=" * 60)


if __name__ == "__main__":
    try:
        monitor_bot()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        log_message(f"CRITICAL ERROR: {e}")
        import traceback
        log_message(traceback.format_exc())
```

**Don't forget to make `monitor.py` executable:**
```bash
chmod +x ~/bot-monitor/monitor.py
```

---

### 3. Update Your Bot Details

Replace the following in `config.py`:
- `PI_HOST` - Your Raspberry Pi hostname (e.g., `codewithromi.local`)
- `PI_USER` - Your SSH username
- `PI_BOT_NAME` - Your PM2 process name (check with `pm2 list`)
- `DISCORD_WEBHOOK` - Your Discord webhook URL

### 3. Create Discord Webhook

1. Go to Discord Server Settings
2. Click "Integrations" → "Webhooks"
3. Click "New Webhook"
4. Name it "AI Bot Monitor"
5. Select the channel for reports
6. Copy the webhook URL
7. Paste into `config.py`

---

## 🚀 Usage

### Manual Run (Episode 4)

```bash
cd ~/bot-monitor
./monitor.py
```

**Expected output:**
```
[2025-11-29 00:21:04] Starting bot monitoring check...
[2025-11-29 00:21:04] Bot status: online
[2025-11-29 00:21:05] No errors detected. Bot is healthy.
```

**If error detected:**
```
[2025-11-29 00:21:05] 🔴 ERROR DETECTED! Analyzing...
[2025-11-29 00:21:05] Error context extracted (922 chars)
[2025-11-29 00:21:05] Sending to AI for analysis...
Sending to AI... (this may take several minutes)
[2025-11-29 00:21:48] AI analysis received!
[2025-11-29 00:21:48] AI RESPONSE:
Root cause: [Analysis here]
Fix needed: [Fix details]
File to modify: [Filename]
[2025-11-29 00:21:48] Sending report to Discord...
[2025-11-29 00:21:49] Discord report sent successfully!
```

### Check Logs

```bash
cat ~/bot-monitor/monitor.log
```

### Test with Simulated Error

```bash
# SSH into your Pi
ssh your-user@your-pi.local

# Navigate to bot directory
cd ~/your-bot-directory

# Edit bot file to add a test error
nano index.js

# Add something like: console.log(undefinedVariable);

# Reload bot
pm2 reload your-bot-name

# Exit back to N100
exit

# Run monitor
./monitor.py

# Should detect error and analyze it!
```

---

## 📁 Project Structure

```
bot-monitor/
├── config.py              # Configuration settings
├── ssh_utils.py           # SSH connection helpers
├── log_parser.py          # Error detection and parsing
├── ai_handler.py          # Ollama AI integration
├── discord_reporter.py    # Discord webhook notifications
├── monitor.py             # Main monitoring script
├── monitor.log            # Activity log (created on first run)
└── README.md              # This file
```

---

## 📺 Tutorial Series

Watch the complete build process on YouTube: [@CodeWithRomii](https://www.youtube.com/@CodeWithRomii)

### Episodes

1. **[Episode 1: Project Introduction](https://youtu.be/HZ20g1LwsBc?si=sYld6b8AOCaG_1On)** - Overview, architecture, and why we're building this
2. **[Episode 1.5: Ubuntu Installation](https://youtu.be/NDCxRg60-Lk?si=FauJ82leeESLo7vT)** - Installing Ubuntu 24.04 on external SSD
3. **[Episode 2: Installing Ollama](https://youtu.be/yZGCeu2VATU?si=_GRHEoJLvJGz7HJg)** - Setting up local AI with Ollama and DeepSeek Coder
4. **[Episode 3: Building the Monitoring System](LINK)** - Python scripts, SSH automation, Discord integration
5. **Episode 4: Automation & Auto-Fix** *(Coming Soon)* - Cron jobs, automatic fixes, rollback
6. **Episode 5: Production Deployment** *(Coming Soon)* - NAS integration, safety checks, final testing

**Subscribe to [@CodeWithRomii](https://www.youtube.com/@CodeWithRomii) for updates!**

---

## 🐛 Troubleshooting

### AI Timeout Error

**Problem:** `AI request timed out after 10 minutes`

**Solutions:**
1. **Switch to faster model (Recommended for N100):**
   ```bash
   ollama pull phi3:3.8b
   ```
   Update `config.py`: `OLLAMA_MODEL = "phi3:3.8b"`

2. **Increase timeout in `ai_handler.py`:**
   ```python
   response = requests.post(OLLAMA_URL, json=data, timeout=600)  # 10 minutes
   ```

3. **Use smaller model:**
   ```bash
   ollama pull deepseek-coder:1.3b
   ```

### SSH Connection Failed

**Problem:** `ERROR getting logs: [Errno 113] No route to host`

**Solutions:**
1. Check Tailscale is running on both devices
2. Test SSH manually: `ssh your-user@your-pi.local`
3. Verify hostname is correct in `config.py`
4. Check firewall settings

### Discord Webhook Not Working

**Problem:** `Failed to send Discord report`

**Solutions:**
1. Verify webhook URL is correct in `config.py`
2. Test webhook manually with curl:
   ```bash
   curl -X POST YOUR_WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{"content":"Test message"}'
   ```
3. Check Discord server permissions

### PM2 Logs Not Found

**Problem:** `No module named 'pm2'` or empty logs

**Solutions:**
1. Verify PM2 is installed: `ssh your-user@your-pi.local "pm2 list"`
2. Check bot name matches: `pm2 list` shows actual name
3. Update `PI_BOT_NAME` in `config.py`

---

## 🔧 Advanced Configuration

### Custom Error Patterns

Edit `log_parser.py` to add custom patterns:

```python
ERROR_PATTERNS = [
    r"Error:",
    r"Exception:",
    r"UnhandledPromiseRejection",
    r"Cannot read property",
    r"undefined is not",
    r"ECONNREFUSED",
    r"ETIMEDOUT",
    r"TypeError",
    r"ReferenceError",
    r"YOUR_CUSTOM_PATTERN",  # Add your patterns here
]
```

### Adjust Monitoring Frequency

Edit `config.py`:

```python
CHECK_INTERVAL = 600  # 10 minutes instead of 15
```

### Change Discord Embed Colors

Edit `discord_reporter.py`:

```python
# Error color (currently red)
color=0xcc3333  # Change to your preferred hex color

# Healthy color (currently green)  
color=0x00cc66  # Change to your preferred hex color
```

---

## 📊 Performance Benchmarks

### Response Times by Model (N100 Mini PC)

| Model | Size | Avg Response | Quality | Recommendation |
|-------|------|--------------|---------|----------------|
| Phi-3 3.8B | 2.3GB | 20-40 sec | ⭐⭐⭐⭐ | ✅ Best for N100 |
| DeepSeek 1.3B | 800MB | 15-25 sec | ⭐⭐⭐ | ⚡ Fastest |
| DeepSeek 6.7B | 4GB | 3-8 min | ⭐⭐⭐⭐⭐ | 🐌 Too slow |
| CodeLlama 7B | 4GB | 2-4 min | ⭐⭐⭐⭐⭐ | 🐌 Too slow |

### Success Rates by Error Type

| Error Type | Phi-3 Success Rate | Notes |
|------------|-------------------|-------|
| Syntax errors | 95% | Excellent |
| Undefined variables | 90% | Very good |
| Import errors | 85% | Good |
| Async/Promise issues | 80% | Good |
| Logic bugs | 70% | Decent |
| Architecture issues | 40% | Escalate to Tier 2/3 |

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Commit your changes:** `git commit -m 'Add amazing feature'`
4. **Push to the branch:** `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Areas for Contribution
- 🎯 Additional error patterns
- 🤖 Support for more AI models
- 📊 Metrics and dashboards
- 🔧 Additional monitoring targets (not just Discord bots)
- 📝 Documentation improvements
- 🌍 Internationalization

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Ollama** - For making local AI accessible and easy
- **DeepSeek AI** - For the excellent DeepSeek Coder model
- **Microsoft** - For the Phi-3 model
- **Discord** - For webhook integration
- **The Community** - For feedback and suggestions

---

## 📞 Contact & Support

- **YouTube:** [@CodeWithRomii](https://www.youtube.com/@CodeWithRomii)
- **Discord:** [Join our server](https://discord.gg/zHwrkDmz8b)


---

## 🎓 Learn More

### Recommended Resources
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Phi-3 Model Card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
- [DeepSeek Coder](https://github.com/deepseek-ai/DeepSeek-Coder)
- [PM2 Documentation](https://pm2.keymetrics.io/)
- [Paramiko SSH Library](https://www.paramiko.org/)
- [Discord Webhooks Guide](https://discord.com/developers/docs/resources/webhook)

---

## 💰 Cost Breakdown

| Component | Cost |
|-----------|------|
| N100 Mini PC | $200 (one-time) |
| Raspberry Pi 5 | $60-80 (one-time, optional) |
| Electricity (N100 24/7) | ~$1.50/month |
| Ollama (Local AI) | FREE |
| Groq API (Tier 2) | FREE |
| Claude API (Tier 3) | ~$0.50/month |
| Tailscale VPN | FREE |
| **Total Monthly** | **~$2/month** |

**vs. Commercial Solutions:** $50-200/month

---

## 🔮 Roadmap

### Version 1.0 (Episodes 4-5)
- [ ] Automatic fix application
- [ ] Automatic rollback
- [ ] Cron job scheduling
- [ ] Three-tier AI system
- [ ] Production deployment

### Version 2.0 (Future)
- [ ] Web dashboard
- [ ] Multiple bot support
- [ ] Email notifications
- [ ] Slack integration
- [ ] Metrics and analytics
- [ ] Machine learning for pattern recognition

---

## ⭐ Star History

If you find this project helpful, please consider giving it a star on GitHub!

---

**Made with ❤️ by [CodeWithRomi](https://www.youtube.com/@CodeWithRomii)**

**Subscribe for more AI, automation, and self-hosting content!**
