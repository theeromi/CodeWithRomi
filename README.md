# 🎯 Homelab Dashboard - Monitor Your Servers from Anywhere

A complete guide to setting up a self-hosted monitoring dashboard using Portainer, Tailscale, and Proxmox. Monitor your Discord bots, Docker containers, and homelab devices from anywhere - all without SSH!

![Dashboard Preview](https://via.placeholder.com/800x400?text=Dashboard+Preview)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation Guide](#installation-guide)
  - [Part 1: Create Proxmox VM](#part-1-create-proxmox-vm)
  - [Part 2: Install Docker](#part-2-install-docker)
  - [Part 3: Install Tailscale](#part-3-install-tailscale)
  - [Part 4: Install Portainer](#part-4-install-portainer)
  - [Part 5: Connect Remote Devices](#part-5-connect-remote-devices)
- [Accessing Your Dashboard](#accessing-your-dashboard)
- [Troubleshooting](#troubleshooting)
- [What's Next](#whats-next)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

✅ **Monitor Discord bots** without SSH  
✅ **Access from anywhere** via Tailscale VPN  
✅ **View real-time logs** in your browser  
✅ **Mobile-friendly** - check your bots on the go  
✅ **Auto-restart** containers on reboot  
✅ **Zero SSH spam** - no more email alerts!  
✅ **Works on any NAS** (Synology, QNAP, TerraMaster, Unraid)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│            TAILSCALE VPN                    │
│     (Access from anywhere - encrypted)      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         PROXMOX VM (Dashboard)              │
│                                             │
│  ┌──────────────────────────────────┐      │
│  │  Portainer (Port 9000)           │      │
│  │  - Docker Management             │      │
│  │  - Container Monitoring          │      │
│  └──────────────────────────────────┘      │
└─────────────────────────────────────────────┘
                    ↓
       ┌────────────┴────────────┐
       ↓                         ↓
┌──────────────┐        ┌──────────────┐
│ TerraMaster  │        │ Raspberry Pi │
│     NAS      │        │              │
│              │        │              │
│ Portainer    │        │ Portainer    │
│   Agent      │        │   Agent      │
│ (Port 9001)  │        │ (Port 9001)  │
│      ↓       │        │      ↓       │
│ Discord Bot  │        │  Test Bot    │
└──────────────┘        └──────────────┘
```

---

## 📦 Prerequisites

### Hardware Requirements
- **Proxmox server** (or any virtualization platform)
- **NAS or server** running Docker (TerraMaster, Synology, QNAP, Unraid, etc.)
- **2GB RAM minimum** for the dashboard VM (6GB recommended)
- **32GB disk space** for the VM

### Software Requirements
- Proxmox VE (or VMware, VirtualBox, etc.)
- Ubuntu 24.04 LTS Server ISO
- Docker on your NAS/remote server
- Tailscale account (free)

### Network Requirements
- Local network access (192.168.x.x or 10.x.x.x)
- Internet connection for downloading packages
- Ability to SSH to devices (just for initial setup)

---

## 🚀 Installation Guide

### Part 1: Create Proxmox VM

**1. Login to Proxmox**
```
https://your-proxmox-ip:8006
```

**2. Click "Create VM"**

**3. Configure VM settings:**

**General Tab:**
- VM ID: `100` (or next available)
- Name: `Dashboard`

**OS Tab:**
- ISO: `ubuntu-24.04-live-server-amd64.iso`

**System Tab:**
- BIOS: `OVMF (UEFI)`
- Add EFI Disk: `✓`
- SCSI Controller: `VirtIO SCSI single`
- Qemu Agent: `✓`

**Disks Tab:**
- Storage: `local-lvm`
- Disk size: `32 GiB`
- Cache: `Write back`
- Discard: `✓`

**CPU Tab:**
- Cores: `2`
- Type: `host`

**Memory Tab:**
- Memory: `6144 MB` (6GB)
- Ballooning: `✓`

**Network Tab:**
- Bridge: `vmbr0`
- Model: `VirtIO (paravirtualized)`

**4. Click "Finish" and start the VM**

**5. Install Ubuntu**

In the console:
- Language: `English`
- Keyboard: `English (US)`
- Installation type: `Ubuntu Server`
- Network: Auto-detect (note the IP address)
- Storage: `Use entire disk` with LVM
- Profile:
  - Name: `dimandem` (or your username)
  - Server name: `dashboard`
  - Username: `dimandem`
  - Password: `[your-secure-password]`
- SSH: **Enable OpenSSH server** ✓ (IMPORTANT!)
- Snaps: Skip all
- Wait for installation to complete
- Reboot

**6. Get IP Address**

Login to the console:
```bash
ip addr show
```

Note the IP (example: `192.168.1.248`)

**7. Set Static IP**

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Replace contents with (adjust IP to match your network):
```yaml
network:
  ethernets:
    ens18:
      addresses:
        - 192.168.1.248/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
  version: 2
```

Apply changes:
```bash
sudo netplan apply
ping google.com  # Test connectivity
```

---

### Part 2: Install Docker

**1. SSH into your VM**

From your computer:
```bash
ssh dimandem@192.168.1.248
# Replace with your username and IP
```

**2. Update system**
```bash
sudo apt update && sudo apt upgrade -y
```

**3. Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

**4. Add user to docker group**
```bash
sudo usermod -aG docker $USER
```

**5. Logout and login again**
```bash
exit
ssh dimandem@192.168.1.248
```

**6. Verify Docker**
```bash
docker --version
# Should show: Docker version 27.x.x
```

---

### Part 3: Install Tailscale

**1. Install Tailscale**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

**2. Start Tailscale**
```bash
sudo tailscale up
```

**3. Authenticate**

Open the URL shown in your browser and login to Tailscale

**4. Get your Tailscale IP**
```bash
tailscale ip -4
```

**Save this IP!** Example: `100.98.237.70`

You now have TWO ways to access your dashboard:
- Local network: `192.168.1.248`
- Anywhere (via Tailscale): `100.98.237.70`

---

### Part 4: Install Portainer

**1. Create data volume**
```bash
docker volume create portainer_data
```

**2. Run Portainer**
```bash
docker run -d \
  -p 9000:9000 \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

**3. Access Portainer**

Open in your browser:
```
http://192.168.1.248:9000
```

Or via Tailscale (from anywhere):
```
http://100.98.237.70:9000
```

**4. First-time setup**
- Create admin username and password
- Click "Get Started"

---

### Part 5: Connect Remote Devices

This is how you connect your NAS or other Docker hosts to Portainer.

#### Install Portainer Agent on Remote Device

**1. SSH into your NAS/server**

Example for TerraMaster (adjust for your device):
```bash
ssh -p 9222 username@192.168.1.197
# Adjust port and IP for your device
```

**2. Install Portainer Agent**
```bash
docker run -d \
  -p 9001:9001 \
  --name portainer_agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:latest
```

**3. Verify agent is running**
```bash
docker ps | grep portainer_agent
```

You should see the agent running on port 9001.

**4. Exit SSH**
```bash
exit
```

**This is the LAST time you need to SSH to this device!** 🎉

#### Add Device to Portainer

**1. In Portainer web UI:**
- Click **"Environments"** (left sidebar)
- Click **"Add environment"**
- Select **"Docker Standalone"**
- Select **"Agent"**

**2. Fill in details:**
- Name: `TerraMaster-NAS` (or your device name)
- Environment URL: `192.168.1.197:9001` (your device IP + port 9001)

**3. Click "Connect"**

You should see "New environment added" notification!

**4. View your containers:**
- Click **"Home"**
- Click on your new environment (e.g., "TerraMaster-NAS")
- Click **"Containers"**

You can now see all containers, view logs, check CPU/RAM, start/stop containers - all without SSH!

---

## 🌍 Accessing Your Dashboard

### Local Network Access
```
http://192.168.1.248:9000
```

### Remote Access (Tailscale)

**On your phone:**
1. Install Tailscale app (iOS/Android)
2. Login and connect
3. Open browser
4. Go to: `http://100.98.237.70:9000`

**On your laptop (anywhere):**
1. Make sure Tailscale is running
2. Browser: `http://100.98.237.70:9000`

**Your dashboard works everywhere with the same Tailscale IP!**

---

## 🛠️ Troubleshooting

### Docker Permission Denied

**Error:** `permission denied while trying to connect to the Docker daemon`

**Solution:**
```bash
# Verify you're in the docker group
groups

# If 'docker' is not listed, add yourself
sudo usermod -aG docker $USER

# IMPORTANT: Logout and login again
exit
ssh username@your-ip
```

### Can't Access Portainer

**Check if container is running:**
```bash
docker ps | grep portainer
```

**Check logs:**
```bash
docker logs portainer
```

**Restart container:**
```bash
docker restart portainer
```

### Portainer Agent Won't Connect

**On the remote device, verify agent is running:**
```bash
docker ps | grep portainer_agent
```

**Check if port 9001 is accessible:**
```bash
# From dashboard VM
curl http://192.168.1.197:9001
# Should return "Portainer agent"
```

**Check firewall on remote device:**
- Make sure port 9001 is allowed
- For NAS devices, check the web UI firewall settings

### VM Won't Auto-Start on Proxmox Boot

**In Proxmox web UI:**
1. Select your VM
2. Options → Start at boot
3. Check the box
4. Click OK

---

## 🚀 What's Next?

This is Part 1 of the complete homelab dashboard series!

**Coming next:**
- Part 2: Homepage Dashboard (device monitoring)
- Part 3: Vaultwarden (password manager)
- Part 4: Outline Wiki (YouTube scripts & notes)
- Part 5: Grafana + YouTube Analytics
- Part 6: Network monitoring & speed tests

**Stay tuned!**

---

## 📹 Video Tutorial

Watch the full video tutorial on YouTube:
- [How I Monitor My Discord Bot from ANYWHERE](https://youtube.com/@CodeWithRomii)

**Subscribe for Part 2!**

---

## 🤝 Contributing

Found an issue? Have a suggestion?

1. Fork this repo
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Portainer](https://www.portainer.io/) - Docker management made easy
- [Tailscale](https://tailscale.com/) - Secure remote access
- [Proxmox](https://www.proxmox.com/) - Virtualization platform
- The homelab community for inspiration!

---

## 📧 Contact

- YouTube: [@CodeWithRomi](https://youtube.com/@CodeWithRomii)
- GitHub: [@theeromi](https://github.com/theeromi)

---

## ⭐ Show Your Support

If this helped you, please:
- ⭐ Star this repository
- 📺 Subscribe to [CodeWithRomi](https://youtube.com/@CodeWithRomii)
- 💬 Share with other homelab enthusiasts!

---

**Built with ❤️ by CodeWithRomi**
