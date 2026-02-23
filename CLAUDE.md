# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Voice-controlled 3D shader rendering for live product demos. Non-technical presenters can say "show me a phone prototype" / "make it blue" / "zoom in" and see instant visual updates. Outputs true alpha channel for disguise (D3) video production workflows.

**Phase 1 (current)**: Natural language → live shader updates
**Phase 2 (planned)**: AR overlay on physical objects with camera/object tracking (Panasonic UE150 FreeD + ArUco/YOLO)

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
Text Input → BRAIN (NLU) → Scene Patch → State Merge → Broadcast → Renderer → Uniforms → Shader
```

**BRAIN** (`BRAIN/src/brain/`):
- `app.py`: WebSocket server, broadcasts to all clients
- `nlu.py`: Regex-based command parser (replace with LLM - see roadmap)
- `state.py`: Scene state with safety clamping (distance 0.8-8.0, FX 0.0-1.5, etc.)
- `protocol.py`: JSON serialization

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

**CRITICAL BUG**: `renderer/src/shaders/raymarch.frag.glsl:72`
Line: `if (t <= 0.0 {` missing closing paren
Fix: `if (t <= 0.0) {`

## Priority Enhancements (from README)

1. **Whisper/faster-whisper** mic input (push-to-talk)
2. Replace `nlu.py` with **LLM → Scene Spec** (constrained to schema via function calling)
3. Add **shape primitives**: cylinder, capsule, torus, rounded_slab in shader
4. **Style presets** mapping to uniform bundles + shader variants
5. **Safety**: validate against schema, ban shader injection, rate limiting, timeouts
6. **Confidence field** so renderer can show when brain is guessing

## Modifying the System

### Adding New Commands
1. Update `BRAIN/src/brain/nlu.py` (or LLM prompt when replaced)
2. Add to `protocol/examples.jsonl`
3. If new scene fields: update `protocol/schema.json`
4. If new uniforms: update `renderer/src/main.js` `applySceneSpec()`
5. If new shader parameters: update `renderer/src/shaders/raymarch.frag.glsl`

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
