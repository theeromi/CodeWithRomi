# 🧠 CodewithRomi – YouTube Tutorial Projects

# 🤖 AI-Powered Discord Bot Monitor

An intelligent monitoring system that watches your Discord bot, detects errors, and **automatically fixes them** using a three-tier AI system. Built for the [CodeWithRomi](https://youtube.com/@CodeWithRomi) YouTube channel.

## ✨ Features

- **🔍 Real-time Error Detection** - Monitors PM2 logs for crashes and errors
- **🧠 Three-Tier AI System** - Uses local AI first (free), escalates to cloud only when needed
- **🔧 Automatic Fixes** - Applies safe, validated fixes without human intervention
- **📊 Daily Status Reports** - Morning and night Discord webhooks with bot health
- **🔄 Smart Rollback** - Automatically reverts bad fixes
- **💾 Backup System** - Every file is backed up before modification

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Monitor (cron job)                    │
├─────────────────────────────────────────────────────────┤
│  1. SSH to Pi → Get PM2 logs                            │
│  2. Parse logs for errors                               │
│  3. If error found:                                     │
│     ├─ Try pattern-based fix (safe)                     │
│     └─ Fall back to AI-generated fix                    │
│  4. Validate JavaScript syntax                          │
│  5. Apply fix → Restart bot → Monitor stability         │
│  6. Rollback if new errors appear                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Three-Tier AI System                        │
├─────────────────────────────────────────────────────────┤
│  Tier 1: Phi-3 (Local via Ollama) - FREE                │
│     ↓ If confidence < 70%                               │
│  Tier 2: Groq Llama 3.3 70B (Cloud) - FREE              │
│     ↓ If failed or low confidence                       │
│  Tier 3: Claude Sonnet (Cloud) - PAID (emergency only)  │
└─────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
bot-monitor/
├── monitor_v2.py      # Main monitoring script
├── config.py          # Configuration and API keys
├── ai_multi_tier.py   # Three-tier AI system
├── log_parser.py      # Error detection from logs
├── ssh_utils.py       # SSH connection to Pi
├── discord_reporter.py # Discord webhook notifications
├── auto_fix.py        # Fix application logic
├── smart_fixer.py     # Pattern-based safe fixes
├── syntax_validator.py # JavaScript validation
├── fix_history.py     # Prevents fix loops
├── codebase_context.py # Fetches code for AI context
└── backups/           # File backups before modifications
```

## 🚀 Setup

### Prerequisites

- Python 3.8+
- SSH access to your bot server (key-based auth recommended)
- PM2 running your Discord bot
- (Optional) Ollama with Phi-3 for local AI

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bot-monitor.git
cd bot-monitor

# Install dependencies
pip install paramiko requests

# Configure your settings
cp config.py.example config.py
nano config.py  # Edit with your settings
```

### Cron Setup

```bash
# Edit crontab
crontab -e

# Add these lines:
# Monitor every 15 minutes
*/15 * * * * cd /path/to/bot-monitor && python3 monitor_v2.py >> cron.log 2>&1

# Daily status reports
0 8 * * * cd /path/to/bot-monitor && python3 monitor_v2.py --status >> cron.log 2>&1
0 22 * * * cd /path/to/bot-monitor && python3 monitor_v2.py --status >> cron.log 2>&1
```

---

## 📄 Code Files

### config.py

Configuration file containing all settings, API keys, and allowed file patterns. This is the central place to configure the monitoring system.

```python
# ============================================
# Pi 5 Connection Settings
# ============================================
PI_HOST = "your-pi-hostname.local"  # Hostname or IP of your Pi
PI_USER = "your-username"           # SSH username
PI_BOT_NAME = "your-bot-name"       # PM2 process name

# Monitoring Settings
CHECK_INTERVAL = 900  # 15 minutes in seconds
LOG_LINES = 100       # How many log lines to check

# ============================================
# THREE-TIER AI CONFIGURATION
# ============================================

# Tier 1: Local AI (Phi-3 via Ollama)
# Running on N100 CPU - needs longer timeout
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:3.8b"
OLLAMA_TIMEOUT = 300  # 5 minutes for slower CPUs

# Tier 2: Groq API (Free - Llama 3.3 70B)
GROQ_API_KEY = "your-groq-api-key-here"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Tier 3: Claude API (Paid - Emergency fallback)
CLAUDE_API_KEY = "your-claude-api-key-here"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# AI Confidence Threshold (0-100)
# If local AI confidence < this, escalate to Tier 2
CONFIDENCE_THRESHOLD = 70

# ============================================
# AUTO-FIX SETTINGS
# ============================================

# Enable automatic fix application
AUTO_FIX_ENABLED = True

# Fix strategy: "ai" (use AI to generate fixes) or "pattern" (use known safe patterns only)
# "pattern" is safer but handles fewer cases
# "ai" is more flexible but can make mistakes
FIX_STRATEGY = "pattern"

# For AI strategy: require this confidence level before auto-applying
AI_FIX_CONFIDENCE_THRESHOLD = 85

# ============================================
# REMOTE BOT SETTINGS (for file modifications)
# ============================================

# Remote bot directory (where the bot code lives on Pi)
PI_BOT_DIR = "/home/your-username/your-bot-directory"

# Files the system is allowed to modify (safety measure)
ALLOWED_FILES = [
    "index.js",
    "utils.js",
    "config.js",
    "commands/*.js",
    "events/*.js",
    "messageCreate.js",
    "voiceStateUpdate.js",
    "config.json",
]

# Discord Webhook for notifications
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# File Paths
import os

HOME = os.path.expanduser("~")
LOG_FILE = os.path.join(HOME, "bot-monitor", "monitor.log")
BACKUP_DIR = os.path.join(HOME, "bot-monitor", "backups")

# How long to monitor after applying a fix (seconds)
POST_FIX_MONITOR_TIME = 600  # 10 minutes

# Maximum fix attempts before giving up
MAX_FIX_ATTEMPTS = 3
```

---

### ai_multi_tier.py

The three-tier AI system that intelligently escalates through AI providers. Starts with free local AI, moves to free cloud AI, and only uses paid API as a last resort.

```python
#!/usr/bin/env python3
"""
Three-Tier AI System for Bot Monitoring
Tier 1: Phi-3 (Local, Free, Fast)
Tier 2: Groq (Cloud, Free, Powerful)
Tier 3: Claude (Cloud, Paid, Most Capable)

IMPROVED: Now includes actual codebase context for better fixes
"""

import requests
import json
import re
from config import (
    OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
    GROQ_API_KEY, GROQ_URL, GROQ_MODEL,
    CLAUDE_API_KEY, CLAUDE_URL, CLAUDE_MODEL,
    CONFIDENCE_THRESHOLD
)


# Structured response format for AI
RESPONSE_FORMAT = """
RESPOND IN THIS EXACT FORMAT:

ROOT_CAUSE: [1-2 sentence explanation]

FIX_TYPE: [replace|append|full_file]

FILE_TO_MODIFY: [exact path, e.g., events/messageCreate.js]

ORIGINAL_CODE:
```javascript
[exact code to replace, if FIX_TYPE is replace]
```

NEW_CODE:
```javascript
[complete replacement code - must be syntactically valid]
```

CONFIDENCE: [0-100]%

IMPORTANT: 
- For FIX_TYPE=replace: Provide the EXACT original code that needs to be replaced
- For FIX_TYPE=full_file: Provide the COMPLETE file content
- For FIX_TYPE=append: Provide code to add at the end
- All code must be syntactically valid JavaScript
"""


def extract_confidence(ai_response: str) -> int:
    """Extract confidence level from AI response."""
    # Check for percentage format first
    percent_match = re.search(r'confidence.*?(\d{1,3})%', ai_response, re.IGNORECASE)
    if percent_match:
        return min(int(percent_match.group(1)), 100)
    
    # Check for CONFIDENCE: format
    conf_match = re.search(r'CONFIDENCE:\s*(\d{1,3})', ai_response, re.IGNORECASE)
    if conf_match:
        return min(int(conf_match.group(1)), 100)
    
    # Check for High/Medium/Low
    if re.search(r'confidence.*?high', ai_response, re.IGNORECASE):
        return 90
    elif re.search(r'confidence.*?medium', ai_response, re.IGNORECASE):
        return 60
    elif re.search(r'confidence.*?low', ai_response, re.IGNORECASE):
        return 30
    
    # Default to medium if not specified
    return 60


def ask_phi3(error_logs: str, bot_status: str = "unknown", codebase_context: str = ""):
    """Tier 1: Local Phi-3 via Ollama
    
    Fast and free, handles most common errors.
    """
    print("🔵 Tier 1: Asking Phi-3 (Local)...")
    
    # Truncate context for smaller model
    context_snippet = codebase_context[:2000] if codebase_context else ""
    
    prompt = f"""You are a Discord bot debugging expert fixing Node.js/JavaScript errors.

Bot Status: {bot_status}

ERROR LOGS:
{error_logs}

{f"RELEVANT CODE CONTEXT:{chr(10)}{context_snippet}" if context_snippet else ""}

CRITICAL: Only suggest fixes using modules/files that EXIST in the codebase.
Do NOT invent new files or modules.

{RESPONSE_FORMAT}"""

    try:
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 1000
            }
        }
        
        response = requests.post(OLLAMA_URL, json=data, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result.get("response", "")
        confidence = extract_confidence(ai_response)
        
        print(f"✅ Phi-3 responded with {confidence}% confidence")
        return ai_response, confidence, None
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Phi-3 timed out (>{OLLAMA_TIMEOUT}s)")
        return None, 0, "Phi-3 timeout"
    except Exception as e:
        print(f"❌ Phi-3 error: {str(e)}")
        return None, 0, str(e)


def ask_groq(error_logs: str, bot_status: str = "unknown", codebase_context: str = ""):
    """Tier 2: Groq API with Llama 3.3 70B
    
    Cloud-based, free, very capable. Used when local AI isn't confident.
    """
    print("🟢 Tier 2: Asking Groq (Llama 3.3 70B)...")
    
    # Truncate context for API limits
    context_snippet = codebase_context[:4000] if codebase_context else ""
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        user_content = f"""Bot Status: {bot_status}

ERROR LOGS:
{error_logs}

{f"=== ACTUAL CODEBASE CONTEXT ==={chr(10)}{context_snippet}" if context_snippet else ""}

CRITICAL: Only use modules/files that EXIST in the codebase shown above.
Do NOT invent new files, handlers, or modules that don't exist.

{RESPONSE_FORMAT}"""
        
        data = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Node.js/Discord.js debugger. Your fixes are applied AUTOMATICALLY to production. Only suggest changes using existing files and modules. Never invent new dependencies."
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"]
        confidence = extract_confidence(ai_response)
        
        print(f"✅ Groq responded with {confidence}% confidence")
        return ai_response, confidence, None
        
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        print(f"⏱️ Groq HTTP error: {error_msg}")
        return None, 0, error_msg
    except requests.exceptions.Timeout:
        print("⏱️ Groq timed out")
        return None, 0, "Groq timeout"
    except Exception as e:
        print(f"❌ Groq error: {str(e)}")
        return None, 0, str(e)


def ask_claude(error_logs: str, bot_status: str = "unknown", codebase_context: str = ""):
    """Tier 3: Claude API (Sonnet 4)
    
    Most capable, costs ~$0.001-0.01 per request. Emergency fallback.
    """
    print("🟣 Tier 3: Asking Claude (Sonnet 4) - Emergency Fallback...")
    
    # Full context for Claude (it can handle more)
    context_snippet = codebase_context[:8000] if codebase_context else ""
    
    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        user_content = f"""You are a world-class Node.js/Discord.js debugging expert. 

Bot Status: {bot_status}

ERROR LOGS:
{error_logs}

{f"=== ACTUAL CODEBASE FILES ==={chr(10)}{context_snippet}" if context_snippet else ""}

CRITICAL: 
- Only use modules/files that EXIST in the codebase shown above
- Do NOT invent new files, handlers, or require statements for non-existent modules
- Your fix will be AUTOMATICALLY APPLIED to production

{RESPONSE_FORMAT}"""
        
        data = {
            "model": CLAUDE_MODEL,
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
        
        response = requests.post(CLAUDE_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result["content"][0]["text"]
        confidence = extract_confidence(ai_response)
        
        print(f"✅ Claude responded with {confidence}% confidence")
        return ai_response, confidence, None
        
    except Exception as e:
        print(f"❌ Claude error: {str(e)}")
        return None, 0, str(e)


def ask_ai_multi_tier(error_logs: str, bot_status: str = "unknown"):
    """Multi-tier AI system with automatic escalation.
    
    Returns: (ai_response, confidence, tier_used, error)
    """
    # Get codebase context for better fixes
    codebase_context = ""
    try:
        from codebase_context import get_full_context_string
        codebase_context = get_full_context_string(error_logs)
        print(f"📂 Fetched {len(codebase_context)} chars of codebase context")
    except Exception as e:
        print(f"⚠️ Could not fetch codebase context: {e}")
    
    # Tier 1: Try Phi-3 (Local)
    response, confidence, error = ask_phi3(error_logs, bot_status, codebase_context)
    
    if response and confidence >= CONFIDENCE_THRESHOLD:
        print(f"✅ Tier 1 success! Confidence: {confidence}%")
        return response, confidence, "phi3-local", None
    
    print(f"⚠️ Tier 1 confidence too low ({confidence}%), escalating...")
    
    # Tier 2: Try Groq (Free Cloud)
    response, confidence, error = ask_groq(error_logs, bot_status, codebase_context)
    
    if response and confidence >= CONFIDENCE_THRESHOLD:
        print(f"✅ Tier 2 success! Confidence: {confidence}%")
        return response, confidence, "groq-llama-70b", None
    
    if error:
        print(f"⚠️ Tier 2 failed ({error}), escalating to Tier 3...")
    else:
        print(f"⚠️ Tier 2 confidence too low ({confidence}%), escalating...")
    
    # Tier 3: Claude (Paid Emergency)
    response, confidence, error = ask_claude(error_logs, bot_status, codebase_context)
    
    if response:
        print(f"✅ Tier 3 success! Confidence: {confidence}%")
        return response, confidence, "claude-sonnet-4", None
    
    # All tiers failed
    print("❌ All AI tiers failed!")
    return None, 0, "all-failed", "All AI services unavailable or low confidence"


if __name__ == "__main__":
    # Test the multi-tier system
    test_error = """
    TypeError: Cannot read property 'username' of undefined
        at Client.<anonymous> (/home/user/bot/events/messageCreate.js:42:30)
    """
    
    response, confidence, tier, error = ask_ai_multi_tier(test_error, "online")
    
    if response:
        print(f"\n{'='*60}")
        print(f"AI Tier Used: {tier}")
        print(f"Confidence: {confidence}%")
        print(f"Response:\n{response}")
    else:
        print(f"\nError: {error}")
```

---

### log_parser.py

Parses PM2 logs to detect errors and extract context. Includes timestamp filtering to avoid reacting to old errors and duplicate detection to prevent alert spam.

```python
import re
from datetime import datetime, timedelta

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
    r"SyntaxError",
    r"MODULE_NOT_FOUND",
    r"Cannot find module",
]

# Patterns to IGNORE (false positives, informational messages)
IGNORE_PATTERNS = [
    r"✅",  # Success messages
    r"Logged in as",
    r"Daily test",
    r"connected",
]

# Track the last error hash to avoid duplicate reports
_last_error_hash = None
_last_error_time = None


def extract_timestamp(line: str) -> datetime:
    """Extract timestamp from a log line if present.
    
    Handles formats like:
    - [2025-12-13T22:17:16.831Z]
    - 2025-12-13 22:17:16
    """
    patterns = [
        r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                ts_str = match.group(1).replace('T', ' ')[:19]
                return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            except:
                pass
    return None


def is_recent_error(line: str, max_age_minutes: int = 30) -> bool:
    """Check if an error line is recent (within max_age_minutes)."""
    timestamp = extract_timestamp(line)
    if not timestamp:
        # If no timestamp, assume it's recent
        return True
    
    age = datetime.utcnow() - timestamp
    return age < timedelta(minutes=max_age_minutes)


def detect_error(logs: str, only_recent: bool = True) -> bool:
    """Check if logs contain any error patterns.
    
    Args:
        logs: The log string to check
        only_recent: If True, only detect errors from the last 30 minutes
    """
    global _last_error_hash, _last_error_time
    
    if not logs:
        return False

    lines = logs.split("\n")
    
    for line in lines:
        # Skip lines that match ignore patterns
        should_ignore = False
        for ignore in IGNORE_PATTERNS:
            if re.search(ignore, line, re.IGNORECASE):
                should_ignore = True
                break
        
        if should_ignore:
            continue
        
        # Check for error patterns
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # If only_recent is True, check the timestamp
                if only_recent and not is_recent_error(line):
                    continue
                
                # Check if this is a duplicate error
                error_hash = hash(line.strip())
                if error_hash == _last_error_hash:
                    # Same error, check if it's been long enough
                    if _last_error_time and (datetime.now() - _last_error_time) < timedelta(minutes=15):
                        continue  # Skip duplicate within 15 minutes
                
                # New error found
                _last_error_hash = error_hash
                _last_error_time = datetime.now()
                return True

    return False


def extract_error_context(logs: str) -> str:
    """Extract the error and surrounding context.
    
    Returns a more comprehensive context including:
    - The error lines
    - Stack trace
    - Any MODULE_NOT_FOUND details
    """
    if not logs:
        return ""

    lines = logs.split("\n")
    error_blocks = []
    current_block = []
    in_error_block = False

    for i, line in enumerate(lines):
        # Check if this line starts an error
        is_error_line = False
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                is_error_line = True
                break
        
        if is_error_line:
            # Start a new error block
            if current_block:
                error_blocks.append('\n'.join(current_block))
            
            # Get context: 3 lines before
            start = max(0, i - 3)
            current_block = lines[start:i+1]
            in_error_block = True
        elif in_error_block:
            # Continue the error block (stack trace, etc.)
            if line.strip().startswith('at ') or line.strip().startswith('1|') or not line.strip():
                current_block.append(line)
            elif 'requireStack' in line or 'code:' in line:
                current_block.append(line)
            else:
                # End of this error block
                in_error_block = False
                error_blocks.append('\n'.join(current_block))
                current_block = []
    
    # Don't forget the last block
    if current_block:
        error_blocks.append('\n'.join(current_block))
    
    if error_blocks:
        # Return the most recent (last) error block
        return error_blocks[-1]
    
    # If no specific error found, return last 20 lines for context
    return "\n".join(lines[-20:])


def get_error_type(error_context: str) -> str:
    """Classify the type of error for better AI prompting."""
    if 'MODULE_NOT_FOUND' in error_context or 'Cannot find module' in error_context:
        return 'missing_module'
    elif 'TypeError' in error_context:
        return 'type_error'
    elif 'ReferenceError' in error_context:
        return 'reference_error'
    elif 'SyntaxError' in error_context:
        return 'syntax_error'
    elif 'undefined' in error_context.lower():
        return 'undefined_error'
    else:
        return 'unknown'
```

---

### monitor_v2.py

The main monitoring script that ties everything together. Runs via cron every 15 minutes, detects errors, attempts fixes, and sends daily status reports to Discord.

```python
#!/usr/bin/env python3
"""
Enhanced AI Bot Monitor v2.0
- Smart pattern-based fixing (safer than pure AI)
- Falls back to AI for unknown errors
- Daily status reports (morning and night)
"""

import time
import datetime
import os
import sys
from ssh_utils import get_pm2_logs, get_bot_status, execute_command
from log_parser import detect_error, extract_error_context
from config import (
    LOG_FILE, AUTO_FIX_ENABLED, BACKUP_DIR, 
    FIX_STRATEGY, AI_FIX_CONFIDENCE_THRESHOLD,
    PI_BOT_DIR
)


def log_message(message: str):
    """Write to log file with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(log_entry.strip())
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to log: {e}")


def try_smart_fix(error_context: str) -> tuple:
    """Try to fix using pattern-based smart fixer first.
    
    Returns: (success, fix_applied, description)
    """
    try:
        from smart_fixer import analyze_and_suggest, fix_undefined_variable, fix_bad_require, get_file_content
        
        result = analyze_and_suggest(error_context)
        
        if not result["can_fix"]:
            return False, False, result["suggestion"]
        
        log_message(f"🧠 Smart fix identified: {result['error_type']}")
        log_message(f"   Confidence: {result['confidence']}%")
        log_message(f"   Suggestion: {result['suggestion']}")
        
        # Apply the fix based on type
        if result["error_type"] == "undefined_variable":
            var_name = result.get("var_name")
            
            # Find which file has the error
            import re
            file_match = re.search(r'at.*?\(([^:]+\.js):\d+', error_context)
            if not file_match:
                return False, False, "Could not identify file from error"
            
            file_path = file_match.group(1).replace(PI_BOT_DIR + '/', '')
            
            success, desc, new_content = fix_undefined_variable(var_name, file_path)
            
            if success and new_content:
                # Apply the fix
                from auto_fix import backup_file
                backup_path = backup_file(file_path)
                
                if backup_path:
                    full_path = os.path.join(PI_BOT_DIR, file_path)
                    cmd = f"""cat > {full_path} << 'EOFSMARTFIX'
{new_content}
EOFSMARTFIX"""
                    output, error = execute_command(cmd)
                    
                    if not error:
                        log_message(f"✅ Smart fix applied: {desc}")
                        return True, True, desc
                    else:
                        log_message(f"❌ Failed to write fix: {error}")
                        return False, False, f"Write failed: {error}"
            
            return False, False, desc
        
        elif result["error_type"] == "module_not_found":
            module_path = result.get("module_path")
            
            # Find which file has the bad require
            import re
            file_match = re.search(r'at.*?\(([^:]+\.js):\d+', error_context)
            if not file_match:
                file_match = re.search(r'Require stack:.*?([^\s]+\.js)', error_context, re.DOTALL)
            
            if not file_match:
                return False, False, "Could not identify file from error"
            
            file_path = file_match.group(1).replace(PI_BOT_DIR + '/', '').replace('/home/user/bot/', '')
            
            success, desc, new_content = fix_bad_require(module_path, file_path)
            
            if success and new_content:
                from auto_fix import backup_file
                backup_path = backup_file(file_path)
                
                if backup_path:
                    full_path = os.path.join(PI_BOT_DIR, file_path)
                    cmd = f"""cat > {full_path} << 'EOFSMARTFIX'
{new_content}
EOFSMARTFIX"""
                    output, error = execute_command(cmd)
                    
                    if not error:
                        log_message(f"✅ Smart fix applied: {desc}")
                        return True, True, desc
            
            return False, False, desc
        
        return False, False, "Unknown fix type"
        
    except Exception as e:
        log_message(f"⚠️ Smart fixer error: {e}")
        return False, False, str(e)


def try_ai_fix(error_context: str, bot_status: str) -> tuple:
    """Try to fix using AI-generated code.
    
    Returns: (success, fix_applied, description)
    """
    try:
        from ai_multi_tier import ask_ai_multi_tier
        from auto_fix import parse_fix_from_ai, apply_fix
        from fix_history import should_attempt_fix, record_fix_attempt
        
        # Check history
        should_try, reason = should_attempt_fix(error_context)
        if not should_try:
            return False, False, f"Blocked by history: {reason}"
        
        # Get AI suggestion
        log_message("🤖 Asking AI for fix suggestion...")
        ai_response, confidence, tier_used, error = ask_ai_multi_tier(error_context, bot_status)
        
        if error:
            return False, False, f"AI error: {error}"
        
        log_message(f"   AI tier: {tier_used}, Confidence: {confidence}%")
        
        # Only apply if confidence is high enough
        if confidence < AI_FIX_CONFIDENCE_THRESHOLD:
            return False, False, f"AI confidence too low ({confidence}% < {AI_FIX_CONFIDENCE_THRESHOLD}%)"
        
        # Parse the fix
        parsed = parse_fix_from_ai(ai_response)
        if len(parsed) == 5:
            file_path, code_to_add, code_to_remove, description, fix_type = parsed
        else:
            file_path, code_to_add, code_to_remove, description = parsed
            fix_type = "replace"
        
        if not file_path or not code_to_add:
            return False, False, "Could not parse AI response"
        
        # Apply the fix
        success, apply_error = apply_fix(file_path, code_to_add, code_to_remove, fix_type)
        
        if success:
            record_fix_attempt(error_context, file_path, code_to_add, True)
            return True, True, description
        else:
            record_fix_attempt(error_context, file_path, code_to_add, False, apply_error)
            return False, False, apply_error
            
    except Exception as e:
        return False, False, str(e)


def monitor_and_fix():
    """Main monitoring function with smart + AI fixing."""
    from discord_reporter import report_error_detected, report_fix_applied, report_fix_failed
    from auto_fix import restart_bot, monitor_after_fix, rollback_from_backup
    
    log_message("=" * 70)
    log_message("🤖 Bot Monitor v2.0 (Smart + AI Hybrid)")
    
    # Get bot status
    bot_status = get_bot_status()
    log_message(f"Bot status: {bot_status}")
    
    # Get logs
    logs, error = get_pm2_logs()
    
    if error:
        log_message(f"❌ ERROR getting logs: {error}")
        return
    
    # Check for errors
    if not detect_error(logs):
        log_message("✅ No errors detected. Bot is healthy.")
        return
    
    log_message("🔴 ERROR DETECTED! Beginning analysis...")
    
    # Extract error context
    error_context = extract_error_context(logs)
    log_message(f"📋 Error context extracted ({len(error_context)} chars)")
    
    if not AUTO_FIX_ENABLED:
        log_message("⚠️ Auto-fix disabled. Sending to Discord...")
        report_error_detected(error_context, "Auto-fix is disabled", bot_status, "disabled", 0)
        return
    
    # Try smart fix first (pattern-based, safer)
    fix_applied = False
    fix_description = ""
    fix_method = ""
    
    if FIX_STRATEGY in ["pattern", "hybrid"]:
        log_message("🧠 Trying smart pattern-based fix...")
        success, applied, desc = try_smart_fix(error_context)
        
        if applied:
            fix_applied = True
            fix_description = desc
            fix_method = "smart-pattern"
    
    # If smart fix didn't work and AI is enabled, try AI
    if not fix_applied and FIX_STRATEGY in ["ai", "hybrid"]:
        log_message("🤖 Trying AI-based fix...")
        success, applied, desc = try_ai_fix(error_context, bot_status)
        
        if applied:
            fix_applied = True
            fix_description = desc
            fix_method = "ai-generated"
        else:
            log_message(f"⚠️ AI fix failed: {desc}")
    
    if not fix_applied:
        log_message("❌ Could not apply any fix. Sending to Discord for manual review...")
        report_error_detected(error_context, f"No automatic fix available. Last attempt: {desc}", bot_status, "no-fix", 0)
        return
    
    # Fix was applied - restart and monitor
    log_message(f"✅ Fix applied via {fix_method}: {fix_description}")
    log_message("🔄 Restarting bot...")
    
    restart_success, restart_error = restart_bot()
    if not restart_success:
        log_message(f"❌ Restart failed: {restart_error}")
        report_fix_failed(error_context, fix_description, restart_error)
        return
    
    # Monitor stability
    log_message("👀 Monitoring bot stability (60 seconds)...")
    time.sleep(10)
    
    # Quick stability check
    new_logs, _ = get_pm2_logs(lines=20)
    if detect_error(new_logs):
        log_message("❌ New errors detected after fix!")
        
        # Rollback
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.backup')])
        if backups:
            latest = os.path.join(BACKUP_DIR, backups[-1])
            import re
            match = re.match(r'(.+?)\.\d{8}_\d{6}\.backup', backups[-1])
            if match:
                original_file = match.group(1)
                rollback_from_backup(latest, original_file)
                restart_bot()
        
        report_fix_failed(error_context, fix_description, "New errors after fix - rolled back")
        return
    
    # Success!
    log_message("✅ SUCCESS! Bot is stable after fix!")
    report_fix_applied(
        error_context=error_context,
        ai_response=fix_description,
        file_modified="auto-detected",
        fix_description=fix_description,
        tier_used=fix_method,
        confidence=95 if fix_method == "smart-pattern" else 80
    )


def send_daily_status():
    """Send daily status report to Discord."""
    from discord_reporter import send_report
    from ssh_utils import get_bot_status, execute_command
    
    bot_status = get_bot_status()
    
    # Get uptime info
    uptime_output, _ = execute_command("pm2 jlist")
    uptime_str = "Unknown"
    restarts = "?"
    memory = "?"
    
    try:
        import json
        processes = json.loads(uptime_output)
        for proc in processes:
            if proc.get("name") == "dimandem-bot":
                # Calculate uptime
                pm2_uptime = proc.get("pm2_env", {}).get("pm_uptime", 0)
                if pm2_uptime:
                    uptime_ms = time.time() * 1000 - pm2_uptime
                    hours = int(uptime_ms / (1000 * 60 * 60))
                    minutes = int((uptime_ms % (1000 * 60 * 60)) / (1000 * 60))
                    uptime_str = f"{hours}h {minutes}m"
                
                restarts = proc.get("pm2_env", {}).get("restart_time", 0)
                memory_bytes = proc.get("monit", {}).get("memory", 0)
                memory = f"{memory_bytes / (1024*1024):.1f} MB"
                break
    except:
        pass
    
    # Get recent error count
    logs, _ = get_pm2_logs(lines=100)
    error_count = 0
    if logs:
        from log_parser import ERROR_PATTERNS
        import re
        for pattern in ERROR_PATTERNS:
            error_count += len(re.findall(pattern, logs, re.IGNORECASE))
    
    # Determine time of day
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        greeting = "🌅 Good Morning"
        period = "morning"
    elif 12 <= hour < 17:
        greeting = "☀️ Good Afternoon"
        period = "afternoon"
    elif 17 <= hour < 21:
        greeting = "🌆 Good Evening"
        period = "evening"
    else:
        greeting = "🌙 Good Night"
        period = "night"
    
    # Status emoji
    if bot_status == "online" and error_count == 0:
        status_emoji = "✅"
        status_text = "All Systems Operational"
        color = 0x00cc66  # Green
    elif bot_status == "online":
        status_emoji = "⚠️"
        status_text = "Online with Recent Errors"
        color = 0xffaa00  # Orange
    else:
        status_emoji = "❌"
        status_text = f"Status: {bot_status}"
        color = 0xcc3333  # Red
    
    fields = [
        {
            "name": "🤖 Bot Status",
            "value": f"{status_emoji} {bot_status.upper()}",
            "inline": True
        },
        {
            "name": "⏱️ Uptime",
            "value": uptime_str,
            "inline": True
        },
        {
            "name": "🔄 Restarts (24h)",
            "value": str(restarts),
            "inline": True
        },
        {
            "name": "💾 Memory",
            "value": memory,
            "inline": True
        },
        {
            "name": "⚠️ Recent Errors",
            "value": str(error_count),
            "inline": True
        },
        {
            "name": "📊 Monitor Status",
            "value": "Active & Watching",
            "inline": True
        }
    ]
    
    send_report(
        title=f"{greeting} - Daily Status Report",
        description=f"**{status_text}**\n\nYour Discord bot monitoring system is active and protecting your bot.",
        color=color,
        fields=fields
    )
    
    log_message(f"📊 Sent {period} status report to Discord")


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            send_daily_status()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python3 monitor_v2.py          # Run normal monitoring check")
            print("  python3 monitor_v2.py --status # Send daily status report")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
    else:
        try:
            monitor_and_fix()
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring stopped by user")
        except Exception as e:
            log_message(f"❌ CRITICAL ERROR: {e}")
            import traceback
            log_message(traceback.format_exc())
```

---

## 🔑 Getting API Keys

### Groq (Free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free
3. Create an API key
4. Add to `config.py`

### Claude (Paid)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account and add credits
3. Generate an API key
4. Add to `config.py`

### Discord Webhook
1. Go to your Discord server settings
2. Integrations → Webhooks → New Webhook
3. Copy the webhook URL
4. Add to `config.py`

## 📺 Watch the Tutorial

Check out the full tutorial on YouTube: [CodeWithRomi](https://youtube.com/@CodeWithRomi)

## 📄 License

MIT License - Feel free to use and modify!

---

Made with ❤️ by [CodeWithRomi](https://youtube.com/@CodeWithRomi)


