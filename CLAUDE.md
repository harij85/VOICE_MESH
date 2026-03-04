# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Computer-vision-powered digital twin generator. Point a camera at a real-world object and the app automatically creates a 3D mesh (digital twin). Users then refine the mesh interactively using voice or text commands — "make it smoother", "change the colour to red", "rotate it". Outputs true alpha channel for disguise (D3) video production workflows.

**Phase 1 (complete)**: Text/voice → live shader & mesh updates (SDF raymarching + Shap-E)
**Phase 2 (current)**: Camera input → object detection → automatic mesh generation (digital twin)
**Phase 3 (planned)**: AR overlay — composite digital twin onto live camera feed with tracking (Panasonic UE150 FreeD + ArUco)

## Development Commands

### BRAIN (Python WebSocket Server)
```bash
cd BRAIN
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"     # Install with dev dependencies (pytest)
brain                       # Starts WebSocket server on port 8765

# Testing
pytest tests/ -v            # Run all tests
pytest tests/test_nlu.py    # Run specific test file
```

### Renderer (Three.js WebGL)
```bash
cd renderer
npm install
npm run dev         # Development server
npm run build       # Production build
npm run preview     # Preview production build

# Testing
npm test            # Run all tests once
npm run test:watch  # Run tests in watch mode
```

### Voice Control (Optional)
```bash
cd BRAIN
pip install -e ".[voice]"  # Install voice dependencies

# Create .env file with:
# ANTHROPIC_API_KEY=your_key_here

# Run voice client
voice                       # Push-to-talk with SPACE key
voice --simple             # Press Enter mode (no keyboard lib)
voice --model tiny         # Use faster Whisper model
voice --no-llm             # Use regex NLU instead of LLM

# Test individual components
python -m brain.audio_capture    # Test microphone
python -m brain.transcription    # Test Whisper
python -m brain.llm_parser       # Test LLM parsing
python -m brain.ws_client        # Test WebSocket
```

**Voice Pipeline:** See `BRAIN/VOICE_PIPELINE_SETUP.md` for step-by-step setup and `BRAIN/VOICE_QUICKSTART.md` for quick start.

### Running Both Services
1. Terminal 1: `cd BRAIN && source .venv/bin/activate && brain`
2. Terminal 2: `cd renderer && npm run dev`
3. Browser: Open renderer URL, press Enter to type commands

### Testing

**Automated Tests:**
- BRAIN: `cd BRAIN && pytest tests/` (61 tests: NLU parsing, state management, safety clamping)
- Renderer: `cd renderer && npm test` (14 tests: scene spec merging)

**Manual Testing:**
- Press Enter in renderer
- Type: `show me a phone prototype` / `make it blue` / `zoom in` / `rotate`
- Check HUD overlay for state updates
- Verify visual changes in shader

## Architecture

### Two-Service WebSocket Design

**Data Flow:**
```
Camera Feed → Object Detection → Mesh Generation (digital twin)
                                        ↓
Voice/Text → BRAIN (NLU) → Scene Patch → State Merge → Broadcast → Renderer → Uniforms → Shader
```

**BRAIN** (`BRAIN/src/brain/`):
- `app.py`: WebSocket server with message validation & rate limiting, broadcasts to all clients
- `nlu.py`: Regex-based command parser (fallback)
- `llm_parser.py`: Claude API command parser (primary NLU)
- `state.py`: Scene state with safety clamping (distance 0.8-8.0, FX 0.0-1.5, etc.)
- `shape_gen.py`: Shap-E text-to-3D mesh generation
- `protocol.py`: JSON serialization
- `vision/` (Phase 2 — planned): Camera capture, object detection, mesh trigger

**Renderer** (`renderer/src/`):
- `main.js`: Three.js setup, uniform management, animation loop
- `wsClient.js`: Auto-reconnecting WebSocket client
- `sceneSpec.js`: Scene data structure (object, material, camera, fx, etc.)
- `shaders/raymarch.frag.glsl`: SDF raymarching shader

**Protocol** (`protocol/schema.json`): JSON Schema defining scene spec structure

### Scene Spec Structure
```javascript
{
  object: {name, category},
  presentation: {mode, style},
  shape_hint: {primitive, features[]},
  material: {preset, color, roughness},
  camera: {orbit, distance, fov},
  lighting: {preset},
  fx: {outline, bloom, alpha}
}
```

### State Synchronization Pattern
- BRAIN maintains single shared `SceneState` across all clients
- Commands → patches (partial updates)
- `state.apply_patch()` does shallow merge + safety clamping
- Broadcast to all renderers after each update
- Renderer merges patch into local scene spec, syncs uniforms

### Shader Architecture
- SDF raymarching (currently single `sdRoundBox` primitive)
- `calcNormal()`, `raymarch()`, `softShadow()` all reference same SDF
- Uniforms mirror scene spec: `u_color`, `u_roughness`, `u_distance`, `u_orbit`, `u_outline`, `u_bloom`, `u_alpha`
- Outputs true alpha: background=0, object=u_alpha

## Known Issues

*(Shader syntax bug at `raymarch.frag.glsl:72` has been fixed — BUG-008/013.)*

## Roadmap

### Phase 2: Camera → Digital Twin (current priority)
1. **Camera capture module** — webcam / USB / RTSP feed via OpenCV
2. **Object detection** — identify object in frame (YOLO / Claude Vision)
3. **Object description** — generate a text description of detected object for mesh generation
4. **Auto-trigger Shap-E** — feed description into existing `shape_gen.py` pipeline
5. **Iterative refinement** — user says "make it taller" / "smoother" to adjust the twin
6. **Reference image overlay** — show camera snapshot alongside generated mesh for comparison

### Phase 2.5: Improved Mesh Quality
7. Replace Shap-E with higher-fidelity model (e.g. InstantMesh, TripoSR, or API-based)
8. Support multi-view capture for better reconstruction
9. Texture extraction from camera image → apply to mesh

### Phase 3: AR Composite
10. Live camera feed as renderer background
11. Camera tracking (FreeD protocol for Panasonic UE150)
12. Object registration (ArUco markers or feature matching)
13. Composite digital twin onto live feed with matched perspective

### Ongoing Improvements
- Replace `nlu.py` regex with **LLM structured output** (Claude tool_use)
- **Style presets** mapping to uniform bundles + shader variants
- **Confidence field** so renderer can show when brain is guessing
- Smooth uniform transitions (lerp on change)

## Modifying the System

### Adding New Commands
1. Update `BRAIN/src/brain/nlu.py` (or LLM prompt when replaced)
2. Add to `protocol/examples.jsonl`
3. If new scene fields: update `protocol/schema.json`
4. If new uniforms: update `renderer/src/main.js` `applySceneSpec()`
5. If new shader parameters: update `renderer/src/shaders/raymarch.frag.glsl`

### Adding Camera/Vision Features
1. New modules go in `BRAIN/src/brain/vision/`
2. Camera capture should be a separate async task feeding frames to detection
3. Detection results trigger mesh generation via existing `shape_gen.py`
4. Camera state (connected, detecting, generating) should be added to scene spec and broadcast
5. Update `protocol/schema.json` with any new message types (e.g. `camera_frame`, `detection`)

### Adding Shader Primitives
To support `shape_hint.primitive: "cylinder"`:
1. Add SDF function to `raymarch.frag.glsl` (e.g., `sdCylinder`)
2. Make `calcNormal()`, `raymarch()`, `softShadow()` switch based on primitive uniform
3. Update `BRAIN/src/brain/nlu.py` CATEGORY_HINTS to recognize objects
4. Update `BRAIN/src/brain/state.py` DEFAULT_SCENE if needed

### Adding Effects
1. Add uniform to `renderer/src/main.js` uniforms object
2. Update `applySceneSpec()` to sync uniform from scene spec
3. Implement in `raymarch.frag.glsl`
4. Add default to `BRAIN/src/brain/state.py` DEFAULT_SCENE
5. Add safety clamp in `state.apply_patch()`
6. Add parsing to `nlu.py`

### Protocol Changes
- Always update `protocol/schema.json` when scene structure changes
- BRAIN and Renderer must stay in sync on scene spec format
- Consider versioning if breaking changes needed

## Alpha Channel Output

- Renderer outputs `alpha=0` for background, `alpha=u_alpha` for object
- For disguise/D3: use NDI with alpha, or SDI key+fill
- `renderer.setClearColor(0x000000, 0)` ensures transparent background
- Shader uses `gl_FragColor = vec4(col, clamp(u_alpha, 0.0, 1.0))`

## Code Conventions

**Python**:
- Async/await for all I/O
- Type hints
- Ruff (line-length=100)
- No `eval()` or arbitrary code execution in NLU

**JavaScript**:
- ES modules
- Vite for bundling
- Shader code in separate `.glsl` files
- Import shaders as `?raw`

**Security**:
- Validate scene messages against schema before applying
- Clamp all numeric parameters (already in `state.py`)
- When adding LLM: use structured output/function calling, constrain to schema
- No arbitrary shader code injection

## Performance Targets

- 60fps shader rendering
- <100ms command → visual update latency
- Raymarching completes in <96 iterations
