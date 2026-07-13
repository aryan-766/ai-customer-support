# Asterisk SIP Bridge Setup Guide
## SAN Software → Asterisk → AI Backend

---

## 📐 Architecture Overview

```
SAN Software (IP-PBX)
    │  SIP INVITE
    ▼
Asterisk PBX                          ← You control this
    │
    ├─ extensions.conf context: [from-san-software]
    │       │
    │       ├─ HTTP POST → localhost:8000/api/v1/sip/san-software/incoming
    │       │                    ↳ call_id milta hai
    │       │
    │       └─ AudioSocket(localhost:5000, <call_id>)
    │
    ▼
sip_bridge.py  [Port 5000]            ← Root folder mein hai
    │
    ├─ WS /ws/sip/{call_id}           ← Asterisk AudioSocket yahan aata hai
    │       ↑↓ G.711 μ-law audio (8kHz)
    │       ↑↓ Convert ↔ PCM16 16kHz
    │
    └─ WS → ws://localhost:8000/ws/call/{call_id}
    
backend/app  [Port 8000]              ← FastAPI backend
    STT → LangGraph Agents → TTS
```

---

## 🚀 Setup Steps

### Step 1: Asterisk mein AudioSocket Module check karo

```bash
# Asterisk CLI mein:
asterisk -rx "module show like audiosocket"
# Should show: chan_audiosocket.so

# Agar nahi hai:
asterisk -rx "module load chan_audiosocket.so"
```

### Step 2: Asterisk mein func_curl load karo

```bash
asterisk -rx "module show like func_curl"
# Should show: func_curl.so

asterisk -rx "module load func_curl.so"
```

### Step 3: SAN Software SIP Trunk configure karo

`asterisk_config/sip.conf` file mein apne SAN Software details bharo:

```ini
[san-software-trunk]
type=peer
host=<YOUR_SAN_SOFTWARE_IP>   ; ← Yahan SAN Software ka IP daalo
port=5060
username=<YOUR_USERNAME>       ; ← SAN Software credentials
secret=<YOUR_PASSWORD>
context=from-san-software
allow=ulaw
```

Asterisk `sip.conf` mein include karo ya copy karo.

### Step 4: Dialplan configure karo

`asterisk_config/extensions.conf` ko Asterisk mein include karo:

```bash
# /etc/asterisk/extensions.conf ke end mein add karo:
#include "extensions_ai_bridge.conf"

# Ya directly copy karo relevant context ko
```

**Note:** Bridge IP confirm karo `extensions.conf` mein:
```ini
[globals]
BRIDGE_HOST=localhost   ; ← Agar sip_bridge.py alag machine pe hai toh IP daalo
BRIDGE_PORT=5000
```

### Step 5: SIP Bridge chalao

```bash
# Project root se:
python sip_bridge.py

# Ya uvicorn directly:
uvicorn sip_bridge:app --host 0.0.0.0 --port 5000
```

### Step 6: Backend chalao

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🧪 Testing

### Manual Test — SIP incoming webhook

```bash
curl -X POST http://localhost:8000/api/v1/sip/san-software/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "caller_id": "9876543210",
    "uniqueid":  "asterisk-test-12345",
    "channel":   "SIP/san-software-00001"
  }'

# Expected response:
# {
#   "status": "success",
#   "call_id": "<uuid>",
#   "ws_url":  "ws://localhost:5000/ws/sip/<uuid>",
#   ...
# }
```

### Bridge Health Check

```bash
curl http://localhost:5000/health
```

### Asterisk se Test Call

```bash
# Asterisk CLI:
asterisk -rx "channel originate SIP/san-software-trunk/<number> extension _X.@from-san-software"
```

---

## 🔧 Audio Codec Settings

| Codec | Asterisk Setting | SIP Bridge Handling |
|-------|-----------------|---------------------|
| G.711 μ-law | `allow=ulaw` | Default — decode_mulaw_bytes() |
| G.711 A-law | `allow=alaw` | Set `SIP_BRIDGE_CODEC=alaw` in .env |
| G.729 | Needs license | NOT supported (use ulaw/alaw) |

`.env` mein set karo:
```ini
SIP_BRIDGE_CODEC=ulaw   # ya alaw
```

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `chan_audiosocket.so not found` | Asterisk 16+ install karo, ya `make menuselect` se enable karo |
| `func_curl.so not found` | `apt install asterisk-curl` ya compile karo |
| Bridge pe connection refused | `sip_bridge.py` chal raha hai check karo port 5000 pe |
| No audio | Codec mismatch — `SIP_BRIDGE_CODEC` aur Asterisk `allow=` match hone chahiye |
| call_id blank | Backend unreachable hai — `http://localhost:8000/health` check karo |

---

## 📁 Files Reference

| File | Purpose |
|------|---------|
| `sip_bridge.py` | Main Asterisk AudioSocket bridge |
| `backend/app/api/v1/san_software.py` | SIP webhook handler (backend side) |
| `asterisk_config/extensions.conf` | Asterisk dialplan template |
| `asterisk_config/sip.conf` | SAN Software SIP trunk config |
| `asterisk_config/modules.conf` | Required Asterisk modules |
