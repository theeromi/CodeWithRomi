# LifeHub Dashboard - Complete Tutorial Script
## CodeWithRomi YouTube Series

---

## **EPISODE 1: Project Setup & Basic Flask App**

### Introduction
"Hey everyone, welcome back to CodeWithRomi! Today we're starting an exciting new series where we'll build a beautiful personal dashboard called LifeHub. This dashboard will show weather, tasks, system stats, and much more. Let's get started!"

### What We'll Build
- Personal dashboard with multiple widgets
- Weather forecast integration
- Task management system
- System monitoring
- Dark mode support
- Responsive design

### Step 1: Project Setup
```bash
# Create project directory
mkdir lifehub-tutorial
cd lifehub-tutorial

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create project structure
mkdir -p templates static/css static/js
```

### Step 2: Install Dependencies
Create `requirements.txt`:
```txt
Flask>=2.0
requests>=2.28.0
psutil>=5.9.0
```

Install:
```bash
pip install -r requirements.txt
```

### Step 3: Basic Flask App
Create `app.py`:
```python
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    now = datetime.now()
    current_time = now.strftime('%I:%M:%S %p')
    current_date = now.strftime('%A, %B %d, %Y')
    user_name = 'Romi'  # Can be made configurable
    
    return render_template('index.html', 
                         user_name=user_name, 
                         current_time=current_time, 
                         current_date=current_date)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
```

### Step 4: Basic HTML Template
Create `templates/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LifeHub</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}" />
  </head>
  <body>
    <header class="top">
      <div class="welcome">
        <h1>Welcome back, {{ user_name }}!</h1>
      </div>
      <div class="meta">
        <div id="current-date">{{ current_date }}</div>
        <div id="current-time">{{ current_time }}</div>
      </div>
    </header>
    <main class="grid">
      <!-- Cards will go here -->
    </main>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
  </body>
</html>
```

### Step 5: Basic CSS
Create `static/css/style.css`:
```css
:root {
  --bg1: #5b21b6;
  --bg2: #ec4899;
  --card: rgba(255,255,255,0.9);
  --text-primary: #0f172a;
  --muted: #6b7280;
}

* { box-sizing: border-box; }

body {
  background: linear-gradient(135deg, var(--bg1), var(--bg2));
  color: var(--text-primary);
  font-family: system-ui, sans-serif;
  margin: 0;
  padding: 32px;
}

.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.top h1 {
  color: white;
  margin: 0;
}

.meta {
  color: rgba(255,255,255,0.85);
  text-align: right;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.card {
  background: var(--card);
  padding: 22px;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(2,6,23,0.3);
}
```

### Step 6: Basic JavaScript
Create `static/js/script.js`:
```javascript
// Update time every second
function updateTime() {
  const el = document.getElementById('current-time');
  if (!el) return;
  const now = new Date();
  let hours = now.getHours();
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  el.textContent = `${hours}:${minutes}:${seconds} ${ampm}`;
}

updateTime();
setInterval(updateTime, 1000);
```

### Testing
Run the app:
```bash
python app.py
```

Visit `http://localhost:5004` in your browser.

**Episode 1 Summary:**
- ✅ Project structure created
- ✅ Flask app running
- ✅ Basic HTML/CSS/JS setup
- ✅ Live clock working

---

## **EPISODE 2: Weather API Integration**

### Introduction
"Welcome back! In this episode, we'll add a weather forecast widget that fetches real-time weather data from an API."

### Step 1: Add Weather Route
Add to `app.py`:
```python
import requests

@app.route('/api/weather')
def get_weather():
    try:
        lat = os.environ.get('WEATHER_LAT', '40.7128')  # Default: NYC
        lon = os.environ.get('WEATHER_LON', '-74.0060')
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&temperature_unit=fahrenheit&timezone=America%2FNew_York&forecast_days=7"
        
        response = requests.get(url, timeout=3)
        data = response.json()
        
        current = data.get('current', {})
        daily = data.get('daily', {})
        
        forecast = []
        if daily and 'time' in daily:
            for i in range(min(7, len(daily['time']))):
                date_obj = datetime.strptime(daily['time'][i], '%Y-%m-%d')
                forecast.append({
                    'day': date_obj.strftime('%a'),
                    'date': date_obj.strftime('%m/%d'),
                    'high': round(daily['temperature_2m_max'][i]),
                    'low': round(daily['temperature_2m_min'][i]),
                    'precip': daily['precipitation_probability_max'][i],
                    'code': daily['weather_code'][i]
                })
        
        return jsonify({
            'current': {
                'temperature': round(current.get('temperature_2m', 0)),
                'humidity': current.get('relative_humidity_2m', 'N/A'),
                'wind_speed': round(current.get('wind_speed_10m', 0), 1),
                'weather_code': current.get('weather_code', 0)
            },
            'forecast': forecast
        })
    except Exception as e:
        return jsonify({'error': 'Weather unavailable'})
```

### Step 2: Add Weather Card to HTML
Add to `templates/index.html` in the grid:
```html
<section class="card weather-card" style="grid-column:span 2">
  <h2>Weather Forecast</h2>
  <div id="weather-content" class="loading">Loading...</div>
</section>
```

### Step 3: Add Weather JavaScript
Add to `static/js/script.js`:
```javascript
async function loadWeather() {
  try {
    const res = await fetch('/api/weather');
    const data = await res.json();
    const el = document.getElementById('weather-content');
    
    if (data.error) {
      el.innerHTML = '<div class="loading">Weather unavailable</div>';
      return;
    }
    
    const curr = data.current;
    const forecast = data.forecast || [];
    
    let html = `
      <div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid var(--border-color)">
        <div class="weather-item"><strong>Now:</strong> ${curr.temperature}°F</div>
        <div class="weather-item"><strong>Humidity:</strong> ${curr.humidity}%</div>
        <div class="weather-item"><strong>Wind:</strong> ${curr.wind_speed} mph</div>
      </div>
    `;
    
    if (forecast.length > 0) {
      html += `<div style="font-size:0.8rem;font-weight:600;margin-bottom:6px">7-Day Forecast</div>`;
      html += `<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;font-size:0.7rem;text-align:center">`;
      forecast.forEach(day => {
        html += `
          <div style="padding:4px;background:var(--task-bg);border-radius:4px">
            <div style="font-weight:600">${day.day}</div>
            <div style="color:var(--muted);font-size:0.65rem">${day.date}</div>
            <div style="color:#ef4444;font-weight:600">${day.high}°</div>
            <div style="color:#3b82f6">${day.low}°</div>
            ${day.precip > 0 ? `<div style="color:#10b981">💧${day.precip}%</div>` : ''}
          </div>
        `;
      });
      html += `</div>`;
    }
    
    el.innerHTML = html;
  } catch(e) {
    document.getElementById('weather-content').textContent = 'Weather unavailable';
  }
}

// Call on page load
document.addEventListener('DOMContentLoaded', function() {
  loadWeather();
});
```

### Step 4: Add Weather CSS
Add to `static/css/style.css`:
```css
.weather-card #weather-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weather-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}
```

**Episode 2 Summary:**
- ✅ Weather API integrated
- ✅ Current weather displayed
- ✅ 7-day forecast shown

---

## **EPISODE 3: Task Management System**

### Introduction
"In this episode, we'll build a complete task management system with localStorage persistence."

### Step 1: Add Tasks Card to HTML
```html
<section class="card tasks-card">
  <h2>Tasks</h2>
  <div id="tasks-input">
    <input type="text" id="task-input" placeholder="Add a task...">
    <button id="add-task-btn">+</button>
  </div>
  <ul id="tasks-list"></ul>
</section>
```

### Step 2: Add Task Management JavaScript
Add to `static/js/script.js`:
```javascript
function loadTasks() {
  const tasks = JSON.parse(localStorage.getItem('lifehub_tasks') || '[]');
  const list = document.getElementById('tasks-list');
  list.innerHTML = tasks.map((task, i) => `
    <li class="task-item ${task.completed ? 'completed' : ''}">
      <input type="checkbox" ${task.completed ? 'checked' : ''} onchange="toggleTask(${i})">
      <span>${task.text}</span>
      <span class="task-delete" onclick="deleteTask(${i})">×</span>
    </li>
  `).join('');
}

function addTask() {
  const input = document.getElementById('task-input');
  const text = input.value.trim();
  if (!text) return;
  
  const tasks = JSON.parse(localStorage.getItem('lifehub_tasks') || '[]');
  tasks.push({text, completed: false, createdAt: new Date().toISOString()});
  localStorage.setItem('lifehub_tasks', JSON.stringify(tasks));
  
  input.value = '';
  loadTasks();
}

function toggleTask(i) {
  const tasks = JSON.parse(localStorage.getItem('lifehub_tasks') || '[]');
  tasks[i].completed = !tasks[i].completed;
  if (tasks[i].completed) {
    tasks[i].completedAt = new Date().toISOString();
  }
  localStorage.setItem('lifehub_tasks', JSON.stringify(tasks));
  loadTasks();
}

function deleteTask(i) {
  const tasks = JSON.parse(localStorage.getItem('lifehub_tasks') || '[]');
  tasks.splice(i, 1);
  localStorage.setItem('lifehub_tasks', JSON.stringify(tasks));
  loadTasks();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  loadTasks();
  
  document.getElementById('add-task-btn').addEventListener('click', addTask);
  document.getElementById('task-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addTask();
  });
});
```

### Step 3: Add Task CSS
```css
#tasks-input {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

#task-input {
  flex: 1;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 0.85rem;
}

#add-task-btn {
  padding: 8px 12px;
  background: #5b21b6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

#tasks-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  background: var(--task-bg);
  border-radius: 4px;
  font-size: 0.85rem;
}

.task-item.completed {
  opacity: 0.6;
}

.task-item.completed span {
  text-decoration: line-through;
}

.task-delete {
  margin-left: auto;
  cursor: pointer;
  color: #ef4444;
  font-weight: bold;
}
```

**Episode 3 Summary:**
- ✅ Task management system
- ✅ localStorage persistence
- ✅ Add, complete, delete tasks

---

## **EPISODE 4: Calendar Widget**

### Introduction
"Let's add a calendar widget that shows the current month with today highlighted."

### Step 1: Add Calendar Route
Add to `app.py`:
```python
import calendar as cal

@app.route('/')
def home():
    # ... existing code ...
    
    # Get current month calendar
    year = now.year
    month = now.month
    month_calendar = cal.monthcalendar(year, month)
    month_name = now.strftime('%B %Y')
    
    return render_template('index.html', 
                         # ... existing params ...
                         month_name=month_name,
                         month_calendar=month_calendar,
                         today=now.day)
```

### Step 2: Add Calendar Card to HTML
```html
<section class="card calendar-card">
  <h2>{{ month_name }}</h2>
  <div id="calendar-content">
    <table class="calendar-table">
      <thead>
        <tr>
          <th>Sun</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th>
        </tr>
      </thead>
      <tbody>
        {% for week in month_calendar %}
        <tr>
          {% for day in week %}
            {% if day == 0 %}
              <td class="empty"></td>
            {% elif day == today %}
              <td class="today">{{ day }}</td>
            {% else %}
              <td>{{ day }}</td>
            {% endif %}
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
```

### Step 3: Add Calendar CSS
```css
.calendar-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.calendar-table th {
  font-weight: 600;
  padding: 4px;
  text-align: center;
}

.calendar-table td {
  padding: 6px 2px;
  text-align: center;
  border: 1px solid rgba(0,0,0,0.05);
}

.calendar-table td.empty {
  background-color: rgba(0,0,0,0.02);
}

.calendar-table td.today {
  background-color: #5b21b6;
  color: white;
  font-weight: bold;
  border-radius: 4px;
}
```

**Episode 4 Summary:**
- ✅ Calendar widget added
- ✅ Current month displayed
- ✅ Today highlighted

---

## **EPISODE 5: System Stats & Monitoring**

### Introduction
"Now we'll add system monitoring to track CPU, memory, disk usage, and more!"

### Step 1: Add System Stats Route
Add to `app.py`:
```python
import psutil

@app.route('/api/system-stats')
def get_system_stats():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        uptime_str = f"{uptime.days}d {int(uptime.total_seconds() // 3600)}h"
        
        return jsonify({
            'cpu': {'percent': cpu_percent},
            'memory': {
                'percent': memory.percent,
                'used': round(memory.used / (1024**3), 2),
                'total': round(memory.total / (1024**3), 2)
            },
            'disk': {
                'percent': disk.percent,
                'used': round(disk.used / (1024**3), 2),
                'total': round(disk.total / (1024**3), 2)
            },
            'uptime': uptime_str
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Step 2: Add System Stats Card
```html
<section class="card system-stats-card">
  <h2>System</h2>
  <div id="system-stats-content" class="loading">Loading...</div>
</section>
```

### Step 3: Add System Stats JavaScript
```javascript
async function loadSystemStats() {
  try {
    const res = await fetch('/api/system-stats');
    const data = await res.json();
    
    if (data.error) {
      document.getElementById('system-stats-content').innerHTML = 
        '<div style="color:#9ca3af">Stats unavailable</div>';
      return;
    }
    
    const getColor = (percent) => {
      if (percent > 80) return 'critical';
      if (percent > 60) return 'warning';
      return 'good';
    };
    
    const el = document.getElementById('system-stats-content');
    el.innerHTML = `
      <div class="stat-row">
        <div class="stat-label">
          <span>CPU</span>
          <span>${data.cpu.percent.toFixed(1)}%</span>
        </div>
        <div class="stat-bar">
          <div class="stat-fill ${getColor(data.cpu.percent)}" 
               style="width:${data.cpu.percent}%"></div>
        </div>
      </div>
      <div class="stat-row">
        <div class="stat-label">
          <span>Memory</span>
          <span>${data.memory.percent.toFixed(1)}%</span>
        </div>
        <div class="stat-bar">
          <div class="stat-fill ${getColor(data.memory.percent)}" 
               style="width:${data.memory.percent}%"></div>
        </div>
        <div class="stat-details">
          <span>${data.memory.used} GB used</span>
          <span>${data.memory.total} GB total</span>
        </div>
      </div>
      <div class="stat-row">
        <div class="stat-label">
          <span>Disk</span>
          <span>${data.disk.percent.toFixed(1)}%</span>
        </div>
        <div class="stat-bar">
          <div class="stat-fill ${getColor(data.disk.percent)}" 
               style="width:${data.disk.percent}%"></div>
        </div>
        <div class="stat-details">
          <span>${data.disk.used} GB used</span>
          <span>${data.disk.total} GB total</span>
        </div>
      </div>
      <div class="uptime-info">⏱️ Uptime: ${data.uptime}</div>
    `;
  } catch(e) {
    document.getElementById('system-stats-content').innerHTML = 
      '<div style="color:#9ca3af">Stats unavailable</div>';
  }
}

function startSystemStatsRefresh() {
  loadSystemStats();
  setInterval(loadSystemStats, 30000); // Refresh every 30 seconds
}

document.addEventListener('DOMContentLoaded', function() {
  startSystemStatsRefresh();
});
```

### Step 4: Add System Stats CSS
```css
.system-stats-card #system-stats-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  font-weight: 600;
}

.stat-bar {
  width: 100%;
  height: 8px;
  background: var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
  background: linear-gradient(90deg, #5b21b6, #ec4899);
}

.stat-fill.critical { background: #ef4444; }
.stat-fill.warning { background: #f59e0b; }
.stat-fill.good { background: #10b981; }

.stat-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--muted);
}

.uptime-info {
  padding: 6px;
  background: var(--task-bg);
  border-radius: 4px;
  font-size: 0.85rem;
  text-align: center;
  font-weight: 600;
}
```

**Episode 5 Summary:**
- ✅ System stats monitoring
- ✅ CPU, memory, disk usage
- ✅ Auto-refresh every 30 seconds

---

## **EPISODE 6: Dark Mode & Responsive Design**

### Introduction
"Let's add dark mode support and make our dashboard fully responsive!"

### Step 1: Add Dark Mode Toggle
Add to HTML header:
```html
<button class="theme-toggle" id="theme-toggle">
  <span id="theme-icon">🌙</span>
  <span id="theme-text">Dark</span>
</button>
```

### Step 2: Add Dark Mode CSS Variables
Update `static/css/style.css`:
```css
[data-theme="dark"] {
  --bg1: #1e1b4b;
  --bg2: #831843;
  --card: rgba(30,41,59,0.95);
  --muted: #94a3b8;
  --text-primary: #f1f5f9;
  --text-secondary: #cbd5e1;
  --border-color: #334155;
  --input-bg: #1e293b;
  --task-bg: #334155;
}
```

### Step 3: Add Dark Mode JavaScript
```javascript
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.getElementById('theme-icon');
const themeText = document.getElementById('theme-text');
const savedTheme = localStorage.getItem('theme') || 'light';

if (savedTheme === 'dark') {
  document.documentElement.setAttribute('data-theme', 'dark');
  themeIcon.textContent = '☀️';
  themeText.textContent = 'Light';
}

themeToggle.addEventListener('click', () => {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  if (currentTheme === 'dark') {
    document.documentElement.removeAttribute('data-theme');
    themeIcon.textContent = '🌙';
    themeText.textContent = 'Dark';
    localStorage.setItem('theme', 'light');
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeIcon.textContent = '☀️';
    themeText.textContent = 'Light';
    localStorage.setItem('theme', 'dark');
  }
});
```

### Step 4: Add Responsive CSS
```css
@media (max-width: 1200px) {
  .grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 900px) {
  .grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .grid { grid-template-columns: 1fr; }
  body { padding: 16px; }
  .top { flex-direction: column; }
}
```

**Episode 6 Summary:**
- ✅ Dark mode implemented
- ✅ Responsive design
- ✅ Mobile-friendly

---

## **EPISODE 7: Advanced Features**

### Introduction
"In this final episode, we'll add news feed, network stats, and drag-and-drop card reordering!"

### Step 1: Add News Route
```python
@app.route('/api/news')
def get_news():
    news = [
        {'title': 'Tech industry sees growth in AI adoption', 'date': 'Today'},
        {'title': 'New renewable energy milestone reached', 'date': 'Yesterday'},
        {'title': 'Space exploration mission succeeds', 'date': '2 days ago'}
    ]
    return jsonify({'news': news})
```

### Step 2: Add Network Stats Route
```python
@app.route('/api/network-stats')
def get_network_stats():
    try:
        net_io = psutil.net_io_counters()
        bytes_sent_gb = round(net_io.bytes_sent / (1024**3), 2)
        bytes_recv_gb = round(net_io.bytes_recv / (1024**3), 2)
        
        return jsonify({
            'bytes_sent_gb': bytes_sent_gb,
            'bytes_recv_gb': bytes_recv_gb,
            'active_connections': len(psutil.net_connections(kind='inet'))
        })
    except Exception as e:
        return jsonify({'error': str(e)})
```

### Step 3: Add Drag-and-Drop
Add to HTML head:
```html
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
```

Add JavaScript:
```javascript
document.addEventListener('DOMContentLoaded', function() {
  const grid = document.querySelector('.grid');
  if (grid && typeof Sortable !== 'undefined') {
    Sortable.create(grid, {
      animation: 200,
      handle: '.card h2',
      onEnd: function() {
        const cards = grid.querySelectorAll('.card');
        const order = Array.from(cards).map(card => 
          Array.from(card.classList).find(c => c.includes('-card'))
        ).filter(Boolean);
        localStorage.setItem('card_order', JSON.stringify(order));
      }
    });
  }
});
```

### Step 4: Add News & Network Cards
```html
<section class="card news-card">
  <h2>News</h2>
  <div id="news-content" class="loading">Loading...</div>
</section>

<section class="card network-card">
  <h2>📡 Network</h2>
  <div id="network-content" class="loading">Loading...</div>
</section>
```

**Episode 7 Summary:**
- ✅ News feed added
- ✅ Network stats
- ✅ Drag-and-drop cards
- ✅ Complete dashboard!

---

## **FINAL PROJECT STRUCTURE**

```
lifehub-tutorial/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

## **DEPLOYMENT TIPS**

1. **Environment Variables:**
   ```bash
   export WEATHER_LAT=40.7128
   export WEATHER_LON=-74.0060
   export LIFEHUB_USER=YourName
   export PORT=5004
   ```

2. **Run as Service (Linux):**
   ```bash
   # Create systemd service
   sudo nano /etc/systemd/system/lifehub.service
   ```
   
   Service file:
   ```ini
   [Unit]
   Description=LifeHub Dashboard
   After=network.target
   
   [Service]
   User=youruser
   WorkingDirectory=/path/to/lifehub-tutorial
   Environment="PATH=/path/to/venv/bin"
   ExecStart=/path/to/venv/bin/python app.py
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Start Service:**
   ```bash
   sudo systemctl enable lifehub
   sudo systemctl start lifehub
   ```

---

## **CLOSING REMARKS**

"Thanks for following along! We've built a complete personal dashboard with:
- Weather forecasts
- Task management
- System monitoring
- Calendar
- Dark mode
- Responsive design

Don't forget to like, subscribe, and hit the bell for more tutorials! See you in the next video!"

---

## **BONUS EPISODES (Optional)**

### Episode 8: Task Analytics with Charts
- Add Chart.js
- Track task completion over time
- Visualize productivity

### Episode 9: Docker Container Monitoring
- SSH integration
- Docker stats display
- Container management

### Episode 10: Service Uptime Monitoring
- Ping multiple services
- Health check dashboard
- Alert system

---

**End of Tutorial Script**

