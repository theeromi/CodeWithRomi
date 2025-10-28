# Pi Alert Setup Guide for Raspberry Pi 4

![Pi Alert](https://img.shields.io/badge/Pi%20Alert-Network%20Monitoring-blue)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4-red)
![License](https://img.shields.io/badge/license-MIT-green)

A beginner-friendly guide to setting up **Pi Alert** on your Raspberry Pi 4 for complete network device monitoring and security.

## 📺 Video Tutorial

Watch the full step-by-step video tutorial on my YouTube channel: **[CodeWithRomi](https://youtube.com/@CodeWithRomi)**

## 📖 What is Pi Alert?

Pi Alert is a powerful network monitoring tool that scans your local network and displays all connected devices in a clean web dashboard. Think of it as a security guard for your home WiFi network!

### ✨ Features

- 🔍 **Real-time device detection** - See all devices on your network instantly
- 🔔 **Customizable alerts** - Get notifications when new devices connect
- 📊 **Device history tracking** - Monitor connection patterns over time
- 🏷️ **Device naming & organization** - Label devices with friendly names
- 🔐 **Network security** - Detect unauthorized devices
- 🌐 **Web-based dashboard** - Access from any device on your network
- 📱 **MAC address vendor lookup** - Identify device manufacturers

## 🛠️ Prerequisites

Before you begin, make sure you have:

| Item | Requirement |
|------|------------|
| **Hardware** | Raspberry Pi 4/5 (2GB+ RAM recommended) |
| **OS** | Raspberry Pi OS (Debian-based, 32-bit or 64-bit) |
| **Storage** | At least 4GB free space on SD card |
| **Network** | Ethernet connection (recommended) or WiFi |
| **Access** | SSH enabled OR keyboard + monitor |
| **Time** | Approximately 15-20 minutes |

## 🚀 Quick Start

### Step 1: Update Your System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Required Dependencies

```bash
sudo apt install git python3 python3-pip apache2 php php-cli php-sqlite3 php-curl php-xml libapache2-mod-php sqlite3 arp-scan curl net-tools -y
```

### Step 3: Download Pi Alert

```bash
cd /var/www/html
sudo git clone https://github.com/pucherot/Pi.Alert.git pialert
```

### Step 4: Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/html/pialert
sudo chmod -R 755 /var/www/html/pialert
```

### Step 5: Run the Installer

```bash
cd /var/www/html/pialert
sudo ./install/pialert_install.sh
```

**Important:** When prompted during installation:
- **Pi-hole integration?** → Answer `N` (No)
- **Email notifications?** → Answer `N` (No)
- **Other settings** → Press `ENTER` to accept defaults

### Step 6: Configure Scanning Permissions

This is crucial for Pi Alert to scan your network:

```bash
sudo visudo
```

In the editor that opens:
1. Scroll to the **bottom** of the file
2. Press `i` to enter INSERT mode
3. Add this line:

```
www-data ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan
```

4. Press `ESC` key
5. Type `:wq` and press `ENTER` to save and exit

### Step 7: Find Your Pi's IP Address

```bash
hostname -I
```

Note down the IP address (e.g., `192.168.1.100`)

### Step 8: Access Pi Alert Dashboard

Open a web browser and navigate to:

```
http://YOUR-PI-IP-ADDRESS/pialert/
```

Replace `YOUR-PI-IP-ADDRESS` with your actual Pi's IP from Step 7.

Example: `http://192.168.1.100/pialert/`

### Step 9: Run Your First Scan (Optional)

To manually trigger a network scan:

```bash
cd /var/www/html/pialert
sudo python3 back/pialert.py updateDevices
```

Refresh your browser to see all detected devices!

## 📱 Usage

### Dashboard Overview

- **Online** - Devices currently connected to your network
- **Down** - Devices that were connected but are now offline
- **All** - Every device that has ever connected

### Customizing Devices

1. Click on any device in the dashboard
2. Give it a friendly name (e.g., "Mom's iPhone", "Smart TV")
3. Set device type and icon
4. Toggle alerts for specific devices

### Setting Up Alerts

- Click on a device
- Toggle the bell icon to enable notifications
- Get alerted when that device connects or disconnects

## 🔧 Troubleshooting

### Web page won't load

```bash
# Check your Pi's IP address
hostname -I

# Restart Apache web server
sudo systemctl restart apache2

# Check Apache status
sudo systemctl status apache2
```

### No devices showing up

- Wait 5 minutes for the automatic scan cycle
- Run a manual scan (see Step 9)
- Verify other devices are actually connected to your network

### Permission errors

```bash
# Reset permissions
sudo chown -R www-data:www-data /var/www/html/pialert
sudo chmod -R 755 /var/www/html/pialert
```

### Database errors

```bash
# Fix database permissions
sudo chown -R www-data:www-data /var/www/html/pialert/db
sudo chmod -R 775 /var/www/html/pialert/db
```

### arp-scan not working

Double-check Step 6. Make sure the line in `/etc/sudoers` is exactly:
```
www-data ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan
```

## 📋 Useful Commands

| Task | Command |
|------|---------|
| Access Pi Alert | `http://YOUR-PI-IP/pialert/` |
| Manual scan | `sudo python3 /var/www/html/pialert/back/pialert.py updateDevices` |
| Find Pi's IP | `hostname -I` |
| Restart Apache | `sudo systemctl restart apache2` |
| View logs | `sudo tail -f /var/www/html/pialert/log/pialert.log` |
| Edit config | `sudo nano /var/www/html/pialert/config/pialert.conf` |

## ⚙️ Configuration

To adjust Pi Alert settings:

```bash
sudo nano /var/www/html/pialert/config/pialert.conf
```

Key settings:
- `SCAN_CYCLE_MINUTES` - How often to scan (default: 5 minutes)
- `DAYS_TO_KEEP_EVENTS` - Event history retention (default: 90 days)
- `SCAN_SUBNETS` - Network subnet to monitor

## 🌐 Remote Access with Tailscale (Optional)

Want to access your Pi Alert dashboard from anywhere? Install Tailscale:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale
sudo tailscale up

# Get your Tailscale IP
tailscale ip -4
```

Then access Pi Alert using your Tailscale IP from any device on your Tailscale network!

## 📚 Additional Resources

- 📄 **[Download PDF Guide](https://github.com/YOUR-USERNAME/pi-alert-setup/releases)** - Complete setup guide with screenshots
- 🎥 **[Video Tutorial](https://youtube.com/@CodeWithRomi)** - Full walkthrough on YouTube
- 🔗 **[Official Pi Alert Repo](https://github.com/pucherot/Pi.Alert)** - Original Pi Alert project
- 💬 **[Discord Community](https://discord.gg/D9p8PKp4Rv)** - Get help and share your setup
- **[Buy Me Ko-fi](https://ko-fi.com/dimandem)**

## 🤝 Contributing

Found an issue or have a suggestion? Feel free to:
- Open an issue
- Submit a pull request
- Comment on the YouTube video
- Share your setup!

## 📝 Notes

- This guide focuses on basic Pi Alert setup without Pi-hole or email notifications
- Pi Alert scans your network every 5 minutes by default
- The dashboard is accessible only from devices on your local network (unless you set up remote access)
- For advanced features like email alerts and Pi-hole integration, check the official Pi Alert documentation

## ⚠️ Security Notice

- Change your default Raspberry Pi password if you haven't already
- Keep your Raspberry Pi OS updated regularly
- Don't expose your Pi Alert dashboard to the public internet without proper security
- Use strong WiFi passwords


## 📄 License

This guide is provided under the MIT License. Pi Alert itself is licensed under GPL-3.0.

## 🙏 Credits

- **Pi Alert** - Created by [pucherot](https://github.com/pucherot/Pi.Alert)
- **Tutorial** - Created by [CodeWithRomi](https://youtube.com/@CodeWithRomi)

## 💬 Support

Having issues? Here's how to get help:

1. Check the [Troubleshooting](#-troubleshooting) section above
2. Watch the [video tutorial](https://youtube.com/@CodeWithRomi) for visual guidance
3. Comment on the YouTube video
4. Open an issue in this repository
5. Check the [official Pi Alert repo](https://github.com/pucherot/Pi.Alert/issues)

---

## ⭐ Show Your Support

If this guide helped you:
- ⭐ Star this repository
- 👍 Like the YouTube video
- 📢 Subscribe to CodeWithRomi
- 🔄 Share with friends who need network monitoring

---

**Made with ❤️ by CodeWithRomi**

*Last updated: October 2025*
