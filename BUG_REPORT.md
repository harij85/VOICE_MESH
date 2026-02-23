# VOICE_MESH Bug Fix Report

**Date**: 2026-02-22
**Codebase**: VOICE_MESH-main
**Scope**: Full codebase audit — BRAIN (Python), renderer (Three.js), shader (GLSL), protocol (JSON Schema)

---

## Summary

| ID | Severity | File | Bug | Status |
|----|----------|------|-----|--------|
| BUG-001 | HIGH | `BRAIN/src/brain/nlu.py` | `"show it"` parsed as object command, never reaches alpha FX | Fixed |
| BUG-002 | MEDIUM | `BRAIN/src/brain/nlu.py` | Style check silently preempts compound object+style commands | Fixed |
| BUG-003 | HIGH | `renderer/src/meshGenerator.js` | `rounded_slab` primitive missing — phones silently render as wrong shape | Fixed |
| BUG-004 | MEDIUM | `BRAIN/src/brain/state.py` | `camera.fov` not clamped — extreme/negative FOV values accepted | Fixed |
| BUG-005 | MEDIUM | `BRAIN/src/brain/state.py` | Nested patch values shared by reference — mutating patch after apply corrupts state | Fixed |
| BUG-006 | HIGH | `renderer/src/sceneSpec.js` | `shape_hint.dimensions` shallow-merged: a dimension patch drops all other keys | Fixed |
| BUG-007 | MEDIUM | `renderer/src/sceneSpec.js` | JS `DEFAULT_SCENE` missing `dimensions` key — diverged from Python defaults | Fixed |
| BUG-008 | LOW | `renderer/src/shaders/raymarch.frag.glsl` | Redundant `if (t > 0.0)` guard after an early return makes background dead code | Fixed |
| BUG-009 | HIGH | `renderer/src/main.js` | Raymarching shader entirely disconnected from renderer — uniforms never set | Documented |
| BUG-010 | HIGH | `BRAIN/src/brain/voice_client.py` | `asyncio.create_task()` called from pynput thread — RuntimeError at runtime | Fixed |
| BUG-011 | MEDIUM | `BRAIN/src/brain/transcription.py` | Global SSL verification bypass affects all HTTPS, not just Whisper download | Documented |
| BUG-012 | MEDIUM | `protocol/schema.json` | `patch` message type missing from schema; `voice_client` role not in enum | Fixed |
| BUG-013 | LOW | `renderer/src/shaders/raymarch.frag.glsl` | Background colour computed on hit path but always overwritten — dead code | Fixed |
| BUG-014 | LOW | `renderer/src/main.js` | Canvas `mousedown` sets `mouseDown=true` before viewport handler checks it — viewport drag broken | Documented |
| BUG-015 | LOW | `BRAIN/src/brain/llm_parser.py` | Outdated Claude model ID `claude-sonnet-4-5-20250929` | Fixed |

---

## Detailed Bug Descriptions

---

### BUG-001 — `"show it"` unreachable FX command
**Severity**: HIGH
**File**: `BRAIN/src/brain/nlu.py`
**Lines**: 39–50 (object regex), 82 (FX check)

**Root Cause**:
The object-show regex `(show me|show|display|i want to see)\s+(an?\s+)?(.+)$` matches `"show it"` with `name="it"`, so the function returns an object patch and never reaches the FX check for `"show it"` on line 82.

```python
# BEFORE (buggy — show object regex fires first)
m = re.search(r"(show me|show|display|i want to see)\s+(an?\s+)?(.+)$", t)
if m:
    ...  # "show it" returns {"object": {"name": "it", ...}}
    return patch

# ... later, unreachable for "show it":
if "fade in" in t or "show it" in t:
    return {"fx": {"alpha": 1.0}}
```

**Fix**: Guard `"show it"` and `"hide it"` _before_ the object regex.

```python
# AFTER — FX guards before object regex
if "hide it" in t:
    return {"fx": {"alpha": 0.0}}
if "show it" in t:
    return {"fx": {"alpha": 1.0}}

m = re.search(r"(show me|show|display|i want to see)\s+(an?\s+)?(.+)$", t)
...
```

---

### BUG-002 — Style keyword preempts compound object+style commands
**Severity**: MEDIUM
**File**: `BRAIN/src/brain/nlu.py`
**Lines**: 28–32 (style check)

**Root Cause**:
The style check runs unconditionally before the object check. `"show me a wireframe phone"` matches `"wireframe"` and returns `{"presentation": {"style": "wireframe"}}` without showing the phone.

```python
# BEFORE (buggy — style always wins)
for kw, style in STYLE_KEYWORDS:
    if kw in t:
        return {"presentation": {"style": style}}
```

**Fix**: When the text is clearly a "show object" command, capture style as part of the object patch instead of short-circuiting.

```python
# AFTER — object regex runs first; style embedded into same patch
m = re.search(r"(show me|show|display|i want to see)\s+(an?\s+)?(.+)$", t)
if m:
    ...
    for kw, style in STYLE_KEYWORDS:
        if kw in t:
            patch["presentation"] = {"style": style}
            break
    ...
    return patch

# Style-only commands (no object trigger)
for kw, style in STYLE_KEYWORDS:
    if kw in t:
        return {"presentation": {"style": style}}
```

---

### BUG-003 — `rounded_slab` primitive missing from meshGenerator
**Severity**: HIGH
**File**: `renderer/src/meshGenerator.js`; root cause in `BRAIN/src/brain/nlu.py`

**Root Cause**:
`nlu.py` CATEGORY_HINTS returns `"rounded_slab"` as the primitive for phones. `meshGenerator.js` has no `rounded_slab` case, so `createGeometry()` falls through to the `default` branch, logs a warning, and silently renders a rounded box with wrong proportions.

```javascript
// meshGenerator.js — no rounded_slab case
switch (primitive) {
  case 'rounded_box': ...
  case 'cylinder': ...
  case 'sphere': ...
  case 'capsule': ...
  case 'torus': ...
  default:
    console.warn(`Unknown primitive: ${primitive}, falling back to rounded_box`);
    return createRoundedBox(dims);  // wrong dimensions for a phone slab
}
```

**Fix**: Add `rounded_slab` to `meshGenerator.js` as a landscape-oriented rounded box (phone screen proportions), and add it to `DEFAULT_DIMENSIONS`.

---

### BUG-004 — `camera.fov` not clamped in state
**Severity**: MEDIUM
**File**: `BRAIN/src/brain/state.py`
**Lines**: 39–60 (`apply_patch`)

**Root Cause**:
`apply_patch()` clamps `camera.distance`, `fx.*`, `material.roughness`, and `shape_hint.dimensions`, but not `camera.fov`. A malicious or buggy client can set `fov: 0` (divide-by-zero in Three.js) or `fov: 360` (inverted view).

**Fix**: Clamp FOV to `[5.0, 150.0]` degrees:

```python
cam["fov"] = clamp(float(cam.get("fov", 35)), 5.0, 150.0)
```

---

### BUG-005 — Nested patch values shared by reference in state
**Severity**: MEDIUM
**File**: `BRAIN/src/brain/state.py`
**Lines**: 34–38 (`apply_patch`)

**Root Cause**:
```python
self.scene[key] = {**self.scene[key], **val}
```
This creates a new top-level dict but nested objects inside `val` (e.g., `val["dimensions"]`, `val["features"]`) are the **same references** as in the original patch dict. If the caller mutates the patch after calling `apply_patch()`, the scene state is corrupted.

**Fix**: Deep-copy the incoming patch at the start of `apply_patch()`:

```python
from copy import deepcopy

def apply_patch(self, patch: Dict[str, Any]) -> None:
    patch = deepcopy(patch)  # isolate from caller
    ...
```

---

### BUG-006 — `shape_hint.dimensions` shallow-merged, drops keys on patch
**Severity**: HIGH
**File**: `renderer/src/sceneSpec.js`
**Lines**: 12 (`mergeScene`)

**Root Cause**:
```javascript
shape_hint: { ...base.shape_hint, ...(patch.shape_hint ?? {}) }
```
If `patch.shape_hint = { dimensions: { width: 1.5 } }`, the spread replaces `base.shape_hint.dimensions` entirely with `{ width: 1.5 }`, losing `height`, `depth`, `radius`, `segments`.

```javascript
// BEFORE — patch with only width drops all other dims
base.shape_hint.dimensions = { width: 0.5, height: 1.0, depth: 0.2, radius: 0.05, segments: 8 }
patch.shape_hint = { dimensions: { width: 1.5 } }
result.shape_hint.dimensions = { width: 1.5 }  // BUG: all other dims lost
```

**Fix**: Deep-merge `dimensions` within `shape_hint`:

```javascript
shape_hint: {
  ...base.shape_hint,
  ...(patch.shape_hint ?? {}),
  dimensions: {
    ...(base.shape_hint?.dimensions ?? {}),
    ...(patch.shape_hint?.dimensions ?? {})
  }
}
```

---

### BUG-007 — JS `DEFAULT_SCENE` missing `dimensions` key
**Severity**: MEDIUM
**File**: `renderer/src/sceneSpec.js`
**Lines**: 2–9

**Root Cause**:
Python's `DEFAULT_SCENE` includes a full `dimensions` object under `shape_hint`. The JS `DEFAULT_SCENE` omits it entirely:

```javascript
// JS (missing dimensions)
shape_hint: { primitive: "rounded_box", features: [] }

// Python (has dimensions)
shape_hint: { primitive: "rounded_box", features: [], dimensions: { width: 0.5, ... } }
```

When BRAIN broadcasts the initial scene, the renderer receives `dimensions` and merges it. But if the renderer starts before BRAIN, or the merge uses the JS default as base, `dimensions` is undefined, causing `undefined` accesses in `meshGenerator.js`.

**Fix**: Add `dimensions` to JS `DEFAULT_SCENE`:

```javascript
shape_hint: {
  primitive: "rounded_box",
  features: [],
  dimensions: { width: 0.5, height: 1.0, depth: 0.2, radius: 0.05, segments: 8 }
}
```

---

### BUG-008 — Redundant `if (t > 0.0)` in shader makes background dead code
**Severity**: LOW
**File**: `renderer/src/shaders/raymarch.frag.glsl`
**Lines**: 120–128

**Root Cause**:
After an early-return guard for the miss case (`t <= 0.0`), the shader still wraps the hit code in `if (t > 0.0)`. This is always true at that point. The background colour computed on line 126 is always overwritten by the hit block.

```glsl
if (t <= 0.0) { gl_FragColor = vec4(0.0,0.0,0.0,0.0); return; }  // early return on miss

vec3 col = vec3(0.02, 0.02, 0.03) + ...;  // background — computed but NEVER used on hit path

if (t > 0.0) {   // ALWAYS true here — dead guard
    col = diff + spec;  // overwrites background
}
```

**Fix**: Remove the redundant `if (t > 0.0)` wrapper.

---

### BUG-009 — Raymarching shader entirely disconnected from renderer
**Severity**: HIGH (Architecture)
**File**: `renderer/src/main.js`
**Status**: Documented (fix requires architectural decision)

**Root Cause**:
`main.js` uses `THREE.MeshStandardMaterial` (PBR rasterization pipeline). The `raymarch.frag.glsl` shader is **never imported or referenced** in `main.js`. None of its uniforms (`u_color`, `u_roughness`, `u_distance`, etc.) are ever set.

The `passthrough.vert.glsl` is similarly unused.

CLAUDE.md describes the system as SDF raymarching, but the renderer is Three.js rasterization with post-processing.

**Recommended Fix**: Wire the shader as a full-screen quad `ShaderMaterial`, pass uniforms from `applySceneSpec()`, and remove the Three.js mesh pipeline — or decide the mesh pipeline is the intended approach and remove the disconnected shader.

---

### BUG-010 — `asyncio.create_task()` called from pynput keyboard thread
**Severity**: HIGH
**File**: `BRAIN/src/brain/voice_client.py`
**Lines**: 105–111 (`run_with_keyboard`)

**Root Cause**:
pynput keyboard listener callbacks run in a separate OS thread. `asyncio.create_task()` requires the calling code to be running inside the asyncio event loop. Calling it from a foreign thread raises `RuntimeError: no running event loop`.

```python
# BEFORE (buggy — called from non-async thread)
def on_press(key):
    if key == keyboard.Key.space and not self.is_recording:
        asyncio.create_task(self.process_voice_command())  # RuntimeError!
```

**Fix**: Capture the event loop reference and use `loop.call_soon_threadsafe` or `asyncio.run_coroutine_threadsafe`:

```python
loop = asyncio.get_event_loop()

def on_press(key):
    if key == keyboard.Key.space and not self.is_recording:
        asyncio.run_coroutine_threadsafe(self.process_voice_command(), loop)
```

---

### BUG-011 — Global SSL verification bypass in transcription module
**Severity**: MEDIUM (Security)
**File**: `BRAIN/src/brain/transcription.py`
**Lines**: 38–40
**Status**: Documented

**Root Cause**:
```python
ssl._create_default_https_context = ssl._create_unverified_context
```
This replaces the global default SSL context for the entire Python process, disabling certificate verification for all subsequent HTTPS requests (not just Whisper model downloads). This is a macOS Python 3.14 workaround applied with too wide a scope.

**Recommended Fix**: Scope SSL bypass only to the model download call, or use `certifi` to fix the root certificate issue.

---

### BUG-012 — `patch` message type and `voice_client` role missing from schema
**Severity**: MEDIUM
**File**: `protocol/schema.json`

**Root Cause**:
`app.py` handles `{"type": "patch", "patch": {...}}` messages (sent by voice client). The schema defines only `hello`, `ping`, `command`, `scene`. Additionally, `ws_client.py` sends `{"type": "hello", "role": "voice_client"}`, but the schema `hello.role` enum only allows `["brain", "renderer"]`.

**Fix**: Add `patch` message definition and add `"voice_client"` to the role enum.

---

### BUG-013 — Background colour computed on hit path — dead code
**Severity**: LOW
**File**: `renderer/src/shaders/raymarch.frag.glsl`
**Lines**: 125–126
**Status**: Fixed with BUG-008

Same root cause as BUG-008. The background `col` initialisation is unreachable on the hit path since `t > 0.0` is always true after the early-return miss guard.

---

### BUG-014 — Viewport drag broken by canvas `mousedown` event ordering
**Severity**: LOW
**File**: `renderer/src/main.js`
**Status**: Documented

**Root Cause**:
DOM events bubble from child to parent. The canvas (`renderer.domElement`) fires `mousedown` first, setting `mouseDown = true`. The viewport div fires `mousedown` second, and its handler checks `!mouseDown` — which is already `false`. `isDraggingViewport` is never set, so viewport drag is inaccessible when clicking on the canvas (which covers the entire viewport).

**Recommended Fix**: Use `capture: true` on the viewport listener or restructure the drag-detection logic.

---

### BUG-015 — Outdated Claude model ID in `llm_parser.py`
**Severity**: LOW
**File**: `BRAIN/src/brain/llm_parser.py`
**Lines**: 95

**Root Cause**:
```python
def __init__(self, ..., model: str = "claude-sonnet-4-5-20250929"):
```
Model `claude-sonnet-4-5-20250929` is outdated. Current model is `claude-sonnet-4-6`.

**Fix**:
```python
def __init__(self, ..., model: str = "claude-sonnet-4-6"):
```

---

## Bugs Fixed vs Documented

| Status | Bugs |
|--------|------|
| **Fixed** | BUG-001, BUG-002, BUG-003, BUG-004, BUG-005, BUG-006, BUG-007, BUG-008, BUG-010, BUG-012, BUG-013, BUG-015 |
| **Documented only** | BUG-009 (architecture), BUG-011 (SSL scope), BUG-014 (event ordering) |

---

## Test Coverage Added

| File | Tests Added | Bugs Covered |
|------|-------------|--------------|
| `BRAIN/tests/test_nlu.py` | +12 tests | BUG-001, BUG-002, BUG-003 |
| `BRAIN/tests/test_state.py` | +8 tests | BUG-004, BUG-005 |
| `BRAIN/tests/test_protocol.py` | +14 tests (new file) | BUG-012 |
| `renderer/src/__tests__/sceneSpec.test.js` | +10 tests | BUG-006, BUG-007 |
| `renderer/src/__tests__/meshGenerator.test.js` | +16 tests (new file) | BUG-003 |
