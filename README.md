# LED Voice Shader

**Voice-controlled 3D rendering for live product demos.** Non-technical presenters can say "show me a phone prototype" or "make it blue" and see instant visual updates with true alpha channel output for professional video production workflows.

![Python Tests](https://img.shields.io/badge/tests-61%20passed-brightgreen)
![Renderer Tests](https://img.shields.io/badge/tests-14%20passed-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)

---

## Features

### ✨ Core Capabilities

- **Natural Language Control** - "show me a tall blue cylinder", "make it wider", "zoom in"
- **Dimensional Control** - Specify width, height, depth, radius via adjectives (tall, wide, small, etc.)
- **Voice Input** (optional) - Push-to-talk with Whisper transcription + Claude LLM parsing
- **Real-time Updates** - <100ms latency from command to visual update
- **True Alpha Channel** - Transparent background for disguise (D3) video production
- **5 Procedural Primitives** - rounded_box, cylinder, sphere, capsule, torus
- **PBR Materials** - Physically-based rendering with roughness control
- **Post-Processing** - Bloom, outline, FXAA anti-aliasing

### 🎨 Natural Language Examples

```
"show me a phone prototype"        → Creates rounded box with phone dimensions
"show me a tall blue cylinder"     → Creates cylinder with height: 2.0, color: blue
"make it wider"                    → Increases width by 20%
"make it red"                      → Changes material color to red
"more bloom"                       → Increases glow effect
"zoom in"                          → Moves camera closer
"stop rotating"                    → Disables auto-orbit
```

---

## Quick Start

**Want to run this in 5 minutes?** See **[QUICKSTART.md](QUICKSTART.md)**

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) Anthropic API key for LLM parsing and voice control

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/LED_VOICE_SHADER.git
cd LED_VOICE_SHADER

# Setup BRAIN (Python WebSocket server)
cd BRAIN
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/  # Verify: 61 passed

# Setup Renderer (Three.js frontend)
cd ../renderer
npm install
npm test  # Verify: 14 passed
```

### Running

**Terminal 1 - BRAIN Server:**
```bash
cd BRAIN
source .venv/bin/activate
brain
```

**Terminal 2 - Renderer:**
```bash
cd renderer
npm run dev
```

**Browser:** Open http://localhost:5173, press **Enter**, type commands!

---

## Architecture

### Two-Service WebSocket Design

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│    Voice     │  HTTP   │    BRAIN     │   WS    │   Renderer   │
│  (optional)  ├────────>│  (Python)    ├────────>│  (Three.js)  │
│              │         │              │  :8765  │              │
│ Whisper+LLM  │         │ NLU → Patch  │         │  Mesh Gen    │
└──────────────┘         └──────────────┘         └──────────────┘
```

**Data Flow:**
```
Text/Voice Input → BRAIN (LLM/Regex NLU) → Scene Patch → WebSocket
  → Renderer → Procedural Mesh → PBR Material → Post-Processing → Pixels
```

### Components

**BRAIN** (`BRAIN/src/brain/`)
- `app.py` - WebSocket server (asyncio), broadcasts to all clients
- `llm_parser.py` - Claude API integration for natural language parsing
- `nlu.py` - Regex-based fallback parser (works without API key)
- `state.py` - Scene state management with safety clamping
- `protocol.py` - JSON serialization

**Renderer** (`renderer/src/`)
- `main.js` - Three.js scene, camera, lights, animation loop
- `meshGenerator.js` - Procedural geometry (5 primitives with dimensional control)
- `postProcessing.js` - EffectComposer with bloom, outline, FXAA
- `wsClient.js` - Auto-reconnecting WebSocket client
- `sceneSpec.js` - Scene data structure and merging logic

**Protocol** (`protocol/schema.json`)
- JSON Schema defining scene spec structure
- Supports object, material, camera, fx, dimensions

### Scene Spec Structure

```javascript
{
  object: { name: "phone", category: "consumer_electronics" },
  shape_hint: {
    primitive: "rounded_box",
    features: [],
    dimensions: { width: 0.35, height: 0.75, depth: 0.08 }  // NEW!
  },
  material: { color: "#4b7bff", roughness: 0.35 },
  camera: { orbit: true, distance: 2.2, fov: 35 },
  fx: { outline: 0.12, bloom: 0.15, alpha: 1.0 }
}
```

### Rendering Pipeline

**Mesh-Based Rendering** (migrated from SDF raymarching):
1. **Scene Patch** arrives via WebSocket
2. **Dimensions parsed** from natural language (adjectives → numeric values)
3. **Procedural mesh** generated via `createGeometry(primitive, dimensions)`
4. **PBR Material** applied with color, roughness, opacity
5. **Lights** illuminate the scene (DirectionalLight + AmbientLight)
6. **Post-Processing** applies bloom, outline, FXAA
7. **Alpha Channel** output (background=0, object=u_alpha)

**Why mesh-based?**
- Enables dimensional control (raymarching had hardcoded sizes)
- Better performance at high resolutions
- Easier to add complex geometry
- Native Three.js material system

---

## Development

### Project Structure

```
LED_VOICE_SHADER/
├── BRAIN/                      # Python WebSocket server
│   ├── src/brain/             # Source code
│   │   ├── app.py            # WebSocket server
│   │   ├── llm_parser.py     # Claude LLM integration
│   │   ├── nlu.py            # Regex-based parser
│   │   ├── state.py          # State management
│   │   └── protocol.py       # JSON serialization
│   ├── tests/                # 61 tests (NLU, state, safety)
│   └── pyproject.toml        # Dependencies
├── renderer/                  # Three.js WebGL renderer
│   ├── src/
│   │   ├── main.js           # Main application
│   │   ├── meshGenerator.js  # Procedural geometry
│   │   ├── postProcessing.js # Effects pipeline
│   │   ├── wsClient.js       # WebSocket client
│   │   └── sceneSpec.js      # Data structures
│   └── package.json          # Dependencies
├── protocol/                  # Shared schema
│   ├── schema.json           # JSON Schema
│   └── examples.jsonl        # Example messages
├── QUICKSTART.md             # 5-minute setup guide
├── CLAUDE.md                 # Developer guide
└── README.md                 # This file
```

### Adding New Commands

See `CLAUDE.md` "Modifying the System" section for detailed guides on:
- Adding new commands to NLU/LLM
- Adding shader primitives
- Adding effects
- Updating the protocol

### Running Tests

```bash
# BRAIN tests (61 tests)
cd BRAIN
pytest tests/ -v

# Renderer tests (14 tests)
cd renderer
npm test

# Test coverage
cd BRAIN
pytest tests/ --cov=brain
```

### Development Commands

See `CLAUDE.md` "Development Commands" section for:
- Voice control setup
- Testing individual components
- Running both services simultaneously

---

## Voice Control Setup (Optional)

Voice control requires an Anthropic API key.

### Quick Voice Setup

```bash
cd BRAIN

# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your_key_here

# Install voice dependencies
pip install -e ".[voice]"

# Run voice client
voice  # Press SPACE to talk, release to process
```

**Voice Pipeline:**
```
Microphone → Whisper (local) → Text → Claude LLM → Scene Patch → WebSocket
```

See `BRAIN/VOICE_QUICKSTART.md` for detailed setup and troubleshooting.

---

## Production Deployment

### Alpha Channel Output

The renderer outputs true alpha channel (background=0, object=opacity):
- **For disguise (D3):** Use NDI with alpha or SDI key+fill
- **For OBS/streaming:** Use browser source with transparency
- **For video editing:** Export with alpha channel preserved

### Performance Targets

- **60fps** rendering at 1080p
- **<100ms** command-to-visual latency
- **<1ms** mesh generation time
- **~5ms** post-processing overhead

### Deployment Options

**WebSocket Server (BRAIN):**
- Production ASGI server: `uvicorn` or `hypercorn`
- Reverse proxy: nginx with WebSocket support
- SSL/TLS for secure WebSocket (wss://)

**Renderer:**
- Static hosting: `npm run build` → deploy `dist/` folder
- CDN: Cloudflare, Netlify, Vercel
- Update WebSocket URL in production build

---

## Roadmap

### Phase 1 (Current) - Natural Language → Live Shader ✓

- [x] WebSocket architecture
- [x] Regex-based NLU
- [x] LLM-based NLU (Claude API)
- [x] Voice control (Whisper + Claude)
- [x] Mesh-based rendering
- [x] Dimensional control
- [x] Safety clamping
- [x] Post-processing effects
- [x] Alpha channel output

### Phase 2 (Planned) - AR Product Demo

**Goal:** Overlay virtual branding on physical objects with camera/object tracking

**Requirements:**
1. **Camera pose tracking** - Panasonic UE150 FreeD integration
2. **Object pose tracking** - ArUco markers + optional YOLO
3. **Compositor pipeline** - Keyed/alpha feed to disguise
4. **Real-time alignment** - Virtual skin locked to physical object rotation

**Use Case:** Presenter picks up a physical product (e.g., unbranded bottle), and virtual branding updates in real-time as they rotate it, outputting live to disguise for broadcast.

### Future Enhancements

- [ ] Multi-object scenes
- [ ] Animation presets
- [ ] Texture mapping
- [ ] Style presets (wireframe, hologram, clay)
- [ ] Confidence scoring for ambiguous commands
- [ ] Undo/redo for scene changes
- [ ] Scene save/load
- [ ] Custom shader injection (with safety sandboxing)

---

## Troubleshooting

### WebSocket Connection Issues

**Symptom:** Renderer shows "WS: connecting..." instead of "WS: connected"

**Solutions:**
- Check BRAIN server is running (`cd BRAIN && brain`)
- Check port 8765 is not blocked by firewall
- Restart both services
- Check browser console for errors (F12)

### Commands Not Working

**Symptom:** Type command, nothing happens

**Solutions:**
- Check HUD shows "WS: connected"
- Verify BRAIN server received command (check terminal output)
- Try simpler command: "make it red"
- Check browser console for JavaScript errors

### Voice Control Issues

**Symptom:** Voice client crashes or doesn't transcribe

**Solutions:**
- Verify .env file has valid ANTHROPIC_API_KEY
- Check microphone permissions
- Try `voice --simple` for simpler input mode
- Use `voice --model tiny` for faster (less accurate) transcription
- Test without voice: use manual commands (press Enter in browser)

### Build/Install Issues

**Symptom:** Module not found, import errors

**Solutions:**
```bash
# Clean reinstall BRAIN
cd BRAIN
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Clean reinstall Renderer
cd ../renderer
rm -rf node_modules dist
npm install
```

### Performance Issues

**Symptom:** Low framerate, laggy updates

**Solutions:**
- Check GPU acceleration enabled in browser
- Reduce post-processing: lower bloom/outline values
- Lower resolution: resize viewport
- Check CPU usage (BRAIN should be <5%)
- Disable auto-orbit if not needed

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/` and `npm test`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

See `CLAUDE.md` for detailed development guide.

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- **Three.js** - WebGL rendering engine
- **Anthropic Claude** - LLM-based natural language parsing
- **OpenAI Whisper** - Speech recognition
- **Vite** - Frontend build tool

---

## Support

- **Documentation:** See `CLAUDE.md` for technical details
- **Quick Setup:** See `QUICKSTART.md` for fast installation
- **Issues:** Open an issue on GitHub
- **Questions:** Check existing issues or start a discussion

---

**Built for live product demos with natural language control.** 🎙️ → 🎨
