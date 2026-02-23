# Quick Start Guide
## Get LED_VOICE_SHADER running in 5 minutes

### Prerequisites

- **Python 3.10+** ([download](https://www.python.org/downloads/))
- **Node.js 18+** ([download](https://nodejs.org/))
- **Git** ([download](https://git-scm.com/downloads))

Verify installation:
```bash
python --version  # Should be 3.10+
node --version    # Should be 18+
```

---

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/LED_VOICE_SHADER.git
cd LED_VOICE_SHADER
```

### 2. Setup BRAIN (WebSocket Server)
```bash
cd BRAIN
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

**Verify BRAIN installation:**
```bash
pytest tests/  # Should see: 61 passed
```

### 3. Setup Renderer (Three.js Frontend)
```bash
cd ../renderer
npm install
```

**Verify renderer installation:**
```bash
npm test  # Should see: 14 passed
```

---

## Running the Application

You need **two terminal windows**:

### Terminal 1: Start BRAIN Server
```bash
cd BRAIN
source .venv/bin/activate  # Windows: .venv\Scripts\activate
brain
```

You should see:
```
[brain] WebSocket server listening on ws://0.0.0.0:8765
```

### Terminal 2: Start Renderer
```bash
cd renderer
npm run dev
```

You should see:
```
Local: http://localhost:5173/
```

---

## First Test

1. **Open browser** to the renderer URL (usually `http://localhost:5173`)
2. **Press Enter key** in the browser window
3. **Type a command** like:
   - `show me a phone prototype`
   - `make it blue`
   - `zoom in`
4. **Press OK** and watch the 3D scene update!

**You should see:**
- The HUD overlay showing current scene state
- Visual updates when you send commands
- WebSocket connection status: "WS: connected"

---

## Test Commands

Try these to explore features:

**Object creation:**
- `show me a phone`
- `show me a tall cylinder`
- `show me a small sphere`

**Colors:**
- `make it red`
- `make it electric blue`
- `change color to #ff00ff`

**Camera:**
- `zoom in`
- `zoom out`
- `stop rotating`
- `start orbiting`

**Effects:**
- `more bloom`
- `more outline`
- `fade out`

**Dimensions (NEW!):**
- `make it wider`
- `make it taller`
- `show me a small blue sphere`

---

## Optional: Voice Control Setup

**Requirements:**
- Anthropic API key ([get one here](https://console.anthropic.com/))

**Setup:**
```bash
cd BRAIN

# Create .env file (copy from template)
cp .env.example .env

# Edit .env and add your API key:
# ANTHROPIC_API_KEY=your_actual_key_here

# Install voice dependencies
pip install -e ".[voice]"

# Start voice client
voice  # Press SPACE to talk, release to process
```

**Voice commands work the same as text:**
- Press and hold SPACE
- Say: "show me a phone prototype"
- Release SPACE
- Watch the scene update!

See `BRAIN/VOICE_QUICKSTART.md` for detailed voice setup.

---

## Troubleshooting

### WebSocket connection fails
- **Check:** Is BRAIN server running? (Terminal 1)
- **Check:** Port 8765 not blocked by firewall
- **Try:** Restart both services

### "Module not found" errors
```bash
# BRAIN:
cd BRAIN
pip install -e ".[dev]"

# Renderer:
cd renderer
npm install
```

### Tests fail
```bash
# Check Python version
python --version  # Must be 3.10+

# Check Node version
node --version  # Must be 18+

# Clean reinstall
rm -rf node_modules .venv
# Then repeat setup steps
```

### Commands don't update the scene
- **Check:** HUD shows "WS: connected" (not "WS: connecting...")
- **Check:** Browser console for errors (F12)
- **Try:** Refresh browser page

### Voice control doesn't work
- **Check:** .env file exists with valid ANTHROPIC_API_KEY
- **Check:** Microphone permissions granted
- **Try:** Use `voice --simple` for simpler input mode
- **Note:** Voice requires API key, but manual commands work without it

---

## What's Next?

- **Read the architecture:** See `CLAUDE.md` for technical details
- **Customize:** Modify `BRAIN/src/brain/nlu.py` to add custom commands
- **Extend:** Add new primitives in `renderer/src/meshGenerator.js`
- **Deploy:** See `README.md` for production deployment options

---

## System Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Voice     │         │    BRAIN    │         │  Renderer   │
│  (optional) │  HTTP   │  (Python)   │  WS     │  (Three.js) │
│             ├────────>│             ├────────>│             │
│  Whisper    │         │  NLU Parser │ :8765   │   WebGL     │
│  + LLM      │         │  WebSocket  │         │   Mesh Gen  │
└─────────────┘         └─────────────┘         └─────────────┘

      ↓                       ↓                       ↓
   Speech              Scene Patches            3D Rendering
```

**Data Flow:**
1. User speaks/types command
2. BRAIN parses natural language → scene patch
3. WebSocket broadcasts patch to renderer
4. Renderer generates mesh with dimensions
5. Visual update in <100ms

---

## Success! ✓

If you can type commands and see the 3D scene update, you're all set!

**Need help?** Check the full `README.md` or open an issue on GitHub.
