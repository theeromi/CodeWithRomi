# VaultAI Infrastructure

Snapshot of how VaultAI runs today on the local PC and the planned migration
to a public-facing deploy on `codewithromi.com`.

---

## Current state — single Windows PC

```
┌─────────────────────────────── Your Windows 11 PC ───────────────────────────────┐
│                                                                                   │
│  HOST PROCESSES (running natively on Windows)                                     │
│  ┌──────────────────────────┐         ┌────────────────────────────────────────┐ │
│  │ Ollama (server + tray)   │  uses   │  eGPU                                  │ │
│  │ pid 25400 + 21988        │ ──────▶ │  (loads 5-30 GB models into VRAM)      │ │
│  │ listens :11434           │         └────────────────────────────────────────┘ │
│  └──────────────────────────┘                                                     │
│            ▲                                                                      │
│            │  http://host.docker.internal:11434                                   │
│            │                                                                      │
│  DOCKER DESKTOP                                                                   │
│  ┌──────────────────────────┐    ┌────────────────────────────────────────────┐  │
│  │ vaultai-backend          │    │ vaultai-frontend                           │  │
│  │ FastAPI + Python 3.11    │    │ nginx serving Vite build                   │  │
│  │ container :8000          │    │ container :80                              │  │
│  │ host port 8000 → 8000    │    │ host port 80 → 8090                        │  │
│  │                          │    │                                            │  │
│  │  /api/auth/*             │ ◀──│ proxies /api/* to backend:8000             │  │
│  │  /api/documents/*        │    │ serves SPA otherwise                       │  │
│  │  /api/chats/*            │    └────────────────────────────────────────────┘  │
│  │  /api/transactions/*     │                                                    │
│  │  /api/settings/*         │                                                    │
│  │  /api/health             │                                                    │
│  └──────────────────────────┘                                                     │
│            ▲                                                                      │
│            │  bind mount  D:\VaultAI\data  →  /data                              │
│            │                                                                      │
│  EXTERNAL D: DRIVE                                                                │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────────────┐  │
│  │ D:\VaultAI\                          │  │ D:\ollama-models\                │  │
│  │ ├── docker-compose.yml               │  │   53.6 GB                        │  │
│  │ ├── .env  (JWT_SECRET, model config) │  │   qwen2.5:14b/32b · phi4         │  │
│  │ ├── backend/  frontend/  README.md   │  │   deepseek-r1:14b · gemma2:9b    │  │
│  │ └── data/                            │  │   llama3.1:8b · nomic-embed-text │  │
│  │     ├── app.db  (SQLite)             │  │                                  │  │
│  │     └── uploads/<user_id>/           │  │   (read by Ollama at runtime,    │  │
│  │         └── *.pdf etc.               │  │    set via OLLAMA_MODELS env)    │  │
│  └──────────────────────────────────────┘  └──────────────────────────────────┘  │
│            ▲                                                                      │
│            │                                                                      │
│   Browser at http://localhost:8090                                                │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Request flow for a chat message

```
browser ──▶ nginx(:8090) ──▶ /api/chats/.../messages
              │
              └──▶ backend(:8000) ──▶ retrieve chunks from SQLite
                                  ──▶ Ollama embeddings (eGPU)
                                  ──▶ build prompt
                                  ──▶ Ollama chat stream (eGPU)
                                  ──▶ SSE token stream back to browser
```

### Why each piece is where it is

- **Ollama on host (not in container)** — gives it direct eGPU access. Containerized
  Ollama on Windows can't talk to the eGPU cleanly.
- **Models on D:** — 53 GB on C: was uncomfortable; D: has 895 GB free. Set via the
  user-level `OLLAMA_MODELS` environment variable (`setx OLLAMA_MODELS D:\ollama-models`).
- **App data on D:** — same drive as models, easy to back up together. SQLite +
  raw uploads in one folder.
- **Backend in a container** — clean Python deps + repeatable build. Reaches Ollama
  via Docker's `host.docker.internal` magic hostname.
- **Frontend behind nginx** — serves the Vite build statically + proxies `/api/*` to
  the backend. Single port (8090) for browsers.

### Persistent processes / services

| Process | How it starts | Lifecycle |
|---|---|---|
| Docker Desktop | Auto on login | Always-on tray |
| Ollama tray app | Auto on login | Spawns the `ollama` server |
| `ollama` server | Spawned by tray | Listens `:11434` |
| `vaultai-backend` | `docker compose up -d` | `restart: unless-stopped` |
| `vaultai-frontend` | `docker compose up -d` | `restart: unless-stopped` |

### Local URLs

| URL | What it serves |
|---|---|
| http://localhost:8090 | Frontend (the app you use) |
| http://localhost:8000 | Backend API (Swagger at `/docs`) |
| http://localhost:8000/api/health | Liveness + Ollama reachability + active models |
| http://localhost:11434 | Ollama API (`/api/tags`, `/api/chat`, `/api/embeddings`) |

---

## Public deploy — Option A: Cloudflare Tunnel (recommended for free beta)

```
                  ╔═══════════════════════════════════════╗
                  ║  Member's browser                      ║
                  ║  https://vaultai.codewithromi.com      ║
                  ╚════════════════════╦═══════════════════╝
                                       │
                                       │  HTTPS
                                       ▼
                  ┌────────────────────────────────────────┐
                  │   Cloudflare edge                      │
                  │   - DNS for codewithromi.com           │
                  │   - TLS termination (free cert)        │
                  │   - DDoS protection                    │
                  └────────────────────┬───────────────────┘
                                       │
                                       │  outbound-only tunnel
                                       │  (no port forwarding!)
                                       ▼
┌─────────────────────────────── Your PC ──────────────────────────────────┐
│                                                                          │
│  ┌──────────────────┐    ┌───────────────────────────────────────────┐   │
│  │ cloudflared      │ ───┤ vaultai-frontend:80                       │   │
│  │ (new container)  │    │ vaultai-backend:8000   (no change)        │   │
│  └──────────────────┘    │ Ollama on host (eGPU)  (no change)        │   │
│                          │ D:\VaultAI\data        (no change)        │   │
│                          └───────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### What changes vs current

- Add one more container to `docker-compose.yml`: `cloudflare/cloudflared` running
  `tunnel run` with a token from your Cloudflare account.
- A `config.yml` mapping `vaultai.codewithromi.com` → `http://vaultai-frontend:80`.
- Cloudflare DNS gets a CNAME pointing to the tunnel.
- Nothing in the app code changes.

### Setup checklist (first-time only)

1. Create a Cloudflare account if you don't have one.
2. Add `codewithromi.com` to Cloudflare → change your registrar's nameservers
   to Cloudflare's two assigned names (one-time, ~24 h propagation).
3. Cloudflare dashboard → **Zero Trust** → Networks → Tunnels → **Create a tunnel**.
4. Pick a name (e.g. `vaultai-home`), copy the tunnel token.
5. Add the token to `.env` (e.g. `CLOUDFLARED_TOKEN=...`).
6. Add this service to `docker-compose.yml`:
   ```yaml
   cloudflared:
     image: cloudflare/cloudflared:latest
     container_name: vaultai-tunnel
     restart: unless-stopped
     command: tunnel run --token ${CLOUDFLARED_TOKEN}
     depends_on:
       - frontend
   ```
7. `docker compose up -d cloudflared`.
8. In the Zero Trust dashboard for that tunnel → **Public Hostnames** → Add
   `vaultai.codewithromi.com` → service `http://vaultai-frontend:80`.
9. Visit `https://vaultai.codewithromi.com` — done.

### Costs

- Cloudflare Tunnel: **$0/mo** (Free plan covers this use case)
- Domain: already owned (`codewithromi.com`)
- Compute: $0 (your existing PC + eGPU)
- Internet: your home upload bandwidth is the throughput cap (~10-50 Mbps typical)

### Privacy nuance

Traffic flows through Cloudflare's edge, where TLS is terminated and re-established
to your tunnel. For a *free trial* tier where members are evaluating the product,
this is acceptable — but if you ever want to make a strict "no third party ever
sees your data" claim for the hosted version, see Option B.

---

## Public deploy — Option B: Tailscale Funnel (no third-party in path)

Same shape as Cloudflare Tunnel, but the tunnel goes to Tailscale's edge instead.
Free for personal use. The trade-off: Tailscale gives you an ugly URL like
`vaultai-home.tail-name.ts.net` — workable for a beta, harder to brand. You can
front it with your own domain via a CNAME but it adds a step.

Same tunneling architecture as Option A; just swap `cloudflared` for the Tailscale
client and run `tailscale funnel 80`.

---

## Public deploy — Option C: VPS + Tailscale to home Ollama (when you scale)

```
                  ╔═══════════════════════════════════════╗
                  ║  Member's browser                      ║
                  ║  https://vaultai.codewithromi.com      ║
                  ╚════════════════════╦═══════════════════╝
                                       │
                                       │  HTTPS (Caddy auto-cert)
                                       ▼
   ┌─────────────────────── Hetzner VPS (~$8/mo) ──────────────────────────┐
   │  Caddy reverse proxy → vaultai-frontend → vaultai-backend             │
   │  (no GPU here)                                                        │
   └────────────────────────────────┬──────────────────────────────────────┘
                                    │
                                    │  Tailscale mesh
                                    │  (only the backend container is on the tailnet)
                                    ▼
┌─────────────────────────── Your PC at home ──────────────────────────────┐
│  Ollama on eGPU                                                          │
│  (the only thing still here — everything else moved to the VPS)          │
└──────────────────────────────────────────────────────────────────────────┘
```

When this is worth the migration:
- More than ~5 active concurrent users (your home internet starts being the bottleneck)
- You want uptime independent of your home electricity / WiFi
- You want a cleaner privacy story (member data lives in EU/US datacenter you control)

Cost: **~$8/mo VPS + your home electricity for the eGPU**.

App data (SQLite + uploads) moves to the VPS too — back it up to B2/S3 nightly.

---

## Migration checklist before flipping the switch

| Item | Status now | Needed for public |
|---|---|---|
| HTTPS | ❌ HTTP localhost | ✅ via Cloudflare Tunnel |
| `JWT_SECRET` | ⚠️ in `.env` | ✅ rotate to long random + startup guard |
| Free-tier limits in code | ❌ none | ✅ max docs / msgs/day / file size / storage |
| User registration | ✅ open | ⚠️ gate by Ghost membership or invite code |
| Backups | ❌ none | ✅ nightly `data/` rsync to second drive + weekly to B2 |
| Logs | ⚠️ stdout only | ⚠️ acceptable for beta; pipe to file later |
| Concurrency limits | ⚠️ FIFO BackgroundTasks | ⚠️ acceptable for ~5 users; real queue at 20+ |
| Privacy policy + ToS | ❌ none | ✅ boilerplate; lawyer later |
| Ghost Members SSO | ❌ separate accounts | ⚠️ nice to have v1, blocker for "members only" UX |
| Rate limiting | ❌ none | ⚠️ should-have (slowapi: 30 chat msgs/min/user) |

---

## Backup strategy (recommended)

What needs to be backed up:
- `D:\VaultAI\data\app.db` — all metadata, users, chats, transactions
- `D:\VaultAI\data\uploads\` — original PDFs/DOCX
- `D:\VaultAI\.env` — JWT secret + tunnel token (treat as secret)

What does NOT need backup:
- `D:\ollama-models\` — re-pullable from the internet for free
- Container images — re-buildable from source

Suggested cadence:
- **Nightly**: `robocopy D:\VaultAI\data E:\backups\vaultai-daily /MIR /R:2`
  to a second drive (catch ransomware / disk failure)
- **Weekly**: rclone push to Backblaze B2 (catch fire / theft / both drives gone)
  — at MVP volume (~100 MB) this costs <$0.10/mo
- Test restoration once before launch — back up, delete `data/`, restore, verify
  the app loads with all docs intact

---

## Useful commands cheat-sheet

```powershell
# Start / stop the stack
docker compose -f D:\VaultAI\docker-compose.yml up -d
docker compose -f D:\VaultAI\docker-compose.yml down

# Rebuild after code changes
docker compose -f D:\VaultAI\docker-compose.yml build
docker compose -f D:\VaultAI\docker-compose.yml up -d

# Watch backend logs
docker logs -f vaultai-backend

# Open a shell inside the backend container
docker exec -it vaultai-backend sh

# Health check (returns ollama: bool, current models)
Invoke-RestMethod http://localhost:8000/api/health

# List Ollama models on host
& 'C:\Users\romai\AppData\Local\Programs\Ollama\ollama.exe' list

# Pull a new model (lands in D:\ollama-models because of OLLAMA_MODELS env var)
& 'C:\Users\romai\AppData\Local\Programs\Ollama\ollama.exe' pull <model-name>

# Manual DB inspection
docker exec -it vaultai-backend sqlite3 /data/app.db
```

---

## Decision log

| Decision | Rationale |
|---|---|
| Ollama on host, not container | eGPU access on Windows |
| Models on D: drive | C: was running low; D: has 895 GB free |
| SQLite (not Postgres) | Single-user / small-team; WAL mode handles ~50 concurrent users |
| FastAPI BackgroundTasks (not Celery/RQ) | Single-process MVP; "real" queue when multi-user load arrives |
| `qwen2.5:14b` default chat model | Good speed/quality tradeoff on the eGPU; 32b too slow, 8b hallucinates |
| `nomic-embed-text` for embeddings | 768-dim, fast, well-supported by Ollama |
| Hybrid retrieval (vector + FTS5 keyword) | Closes the vocabulary gap (e.g. "expense" doesn't appear in bank statement vocab) |
| Pre-computed facts for aggregate queries | Even big models miscount line items in long context; deterministic SQL is the only reliable path |
| Cloudflare Tunnel for first deploy | $0/mo, no port forwarding, real cert; can swap to Tailscale or VPS later |
