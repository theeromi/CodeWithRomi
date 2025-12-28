# Tutorial Setup Guide - Separate Project Directory

This guide helps you set up a **separate project directory** for recreating LifeHub from scratch for your YouTube tutorial, without affecting your current working project.

## Quick Setup

### Option 1: Create in Parent Directory (Recommended)
```bash
# Navigate to parent directory
cd ~

# Create tutorial project
mkdir lifehub-tutorial
cd lifehub-tutorial

# Follow the tutorial script from CodeWithRomi_LifeHub_Tutorial_Script.md
```

### Option 2: Create in Different Location
```bash
# Create in a completely different location
mkdir ~/projects/lifehub-tutorial
cd ~/projects/lifehub-tutorial

# Or use a different name
mkdir ~/youtube-tutorials/lifehub-build
cd ~/youtube-tutorials/lifehub-build
```

## Directory Structure Comparison

### Current Project (DO NOT MODIFY)
```
/home/dimandem/lifehub/
├── app.py
├── templates/
├── static/
└── venv/
```

### Tutorial Project (NEW - Safe to Modify)
```
~/lifehub-tutorial/  (or wherever you choose)
├── app.py
├── templates/
├── static/
└── venv/
```

## Running Both Projects

### Current Project
```bash
cd ~/lifehub
source venv/bin/activate
python app.py  # Runs on port 5002 (default)
```

### Tutorial Project
```bash
cd ~/lifehub-tutorial
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PORT=5004 python app.py  # Use different port!
```

## Port Configuration

To avoid conflicts, use different ports:

| Project | Port | URL |
|---------|------|-----|
| Current LifeHub | 5002 | http://localhost:5002 |
| Tutorial Build | 5004 | http://localhost:5004 |

## Environment Variables

Create separate `.env` files or use different variable names:

### Current Project
```bash
export WEATHER_LAT=40.7128
export WEATHER_LON=-74.0060
export LIFEHUB_USER=Romi
```

### Tutorial Project
```bash
export TUTORIAL_WEATHER_LAT=40.7128
export TUTORIAL_WEATHER_LON=-74.0060
export TUTORIAL_USER=CodeWithRomi
```

## Git Setup (Optional)

If you want to track the tutorial project separately:

```bash
cd ~/lifehub-tutorial
git init
git add .
git commit -m "Initial commit - Episode 1"
```

## Testing Checklist

Before recording each episode:

- [ ] Tutorial project is in separate directory
- [ ] Different port is configured
- [ ] Virtual environment is activated
- [ ] Current project still works
- [ ] No files are shared between projects

## Cleanup After Tutorial

Once you're done recording:

```bash
# Option 1: Keep for reference
# Just leave it as is

# Option 2: Archive it
tar -czf lifehub-tutorial-archive.tar.gz ~/lifehub-tutorial

# Option 3: Delete it
rm -rf ~/lifehub-tutorial
```

## Tips for Recording

1. **Start Fresh Each Episode**: Begin from a clean state matching the episode
2. **Use Different Browser Tab**: Keep current project open in another tab for reference
3. **Clear Browser Cache**: Use incognito mode or clear cache between episodes
4. **Document Changes**: Note what you're adding in each episode
5. **Test Before Recording**: Make sure everything works before hitting record

## Episode-by-Episode Setup

### Episode 1: Basic Setup
```bash
mkdir ~/lifehub-tutorial
cd ~/lifehub-tutorial
python3 -m venv venv
source venv/bin/activate
# Follow Episode 1 steps
```

### Episode 2-7: Incremental Build
```bash
cd ~/lifehub-tutorial
source venv/bin/activate
# Add features as shown in each episode
```

## Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
lsof -i :5004

# Kill the process or use different port
PORT=5005 python app.py
```

### Virtual Environment Issues
```bash
# Recreate venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Import Errors
```bash
# Make sure you're in the right directory
pwd  # Should show ~/lifehub-tutorial

# Check virtual environment
which python  # Should show venv path
```

---

**Remember**: Your current project at `/home/dimandem/lifehub` is safe and won't be affected by the tutorial project!

