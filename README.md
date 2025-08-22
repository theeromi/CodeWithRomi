# 🧠 Romi Assistant – Voice-Activated AI Assistant in Python

Welcome to **Romi Assistant**, a personal AI assistant that listens, speaks, and responds intelligently using **Python**, **OpenAI GPT-4**, and **voice commands**.

> 🎤 Built from scratch on macOS using only local tools and the OpenAI API — no browser required.

---

## 🚀 Features
- 🎙️ Voice recognition with `speech_recognition`
- 🤖 Smart replies using GPT-4 via OpenAI API
- 🗣️ Text-to-speech responses with `pyttsx3`
- 🎧 Runs fully in Terminal, no GUI needed
- 🔐 Secure API key handling using `.env`
- 🧼 Handles ambient noise, silence, and clean exits

---

## 🛠 Requirements
- Python 3.9+
- macOS, Linux, or Windows (tested on macOS Sequoia)
- OpenAI API Key

---

## 📦 Installation

1. **Clone this repo:**
```bash
git clone https://github.com/theeromi/CodeWithRomi.git
cd CodeWithRomi
git checkout Ai-Assistant
cd romi-assistant
```

2. **Create and activate a virtual environment:**
```bash
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. **Install the required packages:**
```bash
pip install -r requirements.txt
```

4. **Create a `.env` file and add your OpenAI API key:**
```bash
echo "OPENAI_API_KEY=your_openai_key_here" > .env
```

> Get your key from: https://platform.openai.com/account/api-keys

---

## 🧠 Usage

Run the assistant:
```bash
python main.py
```

Then speak something like:
- “What’s the capital of France?”
- “Tell me a programming joke.”
- “Explain binary search.”
- Say “exit” or “quit” to close the assistant.

---

## 📁 File Structure

```
romi-assistant/
├── main.py              # Core voice assistant script
├── .env                 # API key (not tracked in git)
├── env/                 # Virtual environment
└── requirements.txt     # All dependencies
```

---

## ✅ Known Improvements Made
- Updated for latest OpenAI SDK (v1.x) using `client.chat.completions.create()`
- Adjusted speech speed and added mic pause tuning
- Prevents GPT from responding to noise or Romi's own voice
- Graceful shutdown with Ctrl+C
- Delay after speech to avoid echo-triggering

---

## 📹 Featured in:
This assistant was featured in a full YouTube build on **CodeWithRomi**.  
Watch the full tutorial here → *https://youtu.be/-7xzzUEzhuM*

---

## 🙌 Credits
Developed by [@CodewithRomi](https://github.com/theeromi)  
Voice + AI + Python = Magic
