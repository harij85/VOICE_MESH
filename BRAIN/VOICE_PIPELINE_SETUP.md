# Voice Pipeline Setup Guide

This guide walks through setting up the voice-controlled LED Voice Shader pipeline step by step, with testing at each stage.

## Prerequisites

```bash
cd BRAIN
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## Step 1: Audio Capture Testing

**Install dependencies:**
```bash
pip install pyaudio
```

**Test microphone capture:**
```bash
python -m brain.audio_capture
```

**Expected output:**
- Lists available audio devices
- Records 3 seconds of audio
- Saves to `test_recording.wav`
- You can play the file to verify it captured your voice

**Troubleshooting:**
- macOS: You may need to grant microphone permission
- Linux: May need `sudo apt-get install portaudio19-dev python3-pyaudio`
- Windows: PyAudio should install directly via pip

**✓ Test passes when:** You can play `test_recording.wav` and hear your voice clearly.

---

## Step 2: Whisper Transcription

**Install Whisper:**
```bash
pip install openai-whisper
```

**Test transcription:**
```bash
python -m brain.transcription
```

**Expected output:**
- Uses `test_recording.wav` from Step 1
- Prints transcribed text
- Shows processing time

**✓ Test passes when:** The transcription accurately reflects what you said in the recording.

---

## Step 3: LLM Command Extraction

**Setup:**
1. Create a `.env` file in the `BRAIN` directory:
```bash
ANTHROPIC_API_KEY=your_api_key_here
```

2. Get an API key from: https://console.anthropic.com/

**Install dependencies:**
```bash
pip install anthropic python-dotenv
```

**Test LLM parsing:**
```bash
python -m brain.llm_parser
```

**Expected output:**
- Takes sample commands like "show me a red phone"
- Returns structured JSON with object, color, etc.
- Shows multiple test cases

**✓ Test passes when:** The LLM correctly extracts object names, colors, and actions from natural language.

---

## Step 4: WebSocket Client

**Test WebSocket communication:**
```bash
# Terminal 1: Start the brain server
brain

# Terminal 2: Run WebSocket client test
python -m brain.ws_client
```

**Expected output:**
- Connects to brain on localhost:8765
- Sends test command
- Receives scene update
- Prints confirmation

**✓ Test passes when:** The client successfully connects and sends a command that updates the scene.

---

## Step 5: Full Voice Pipeline

**Install all dependencies:**
```bash
pip install -e ".[voice]"
```

**Run the voice client:**
```bash
# Terminal 1: Start brain server
brain

# Terminal 2: Start renderer
cd ../renderer
npm run dev

# Terminal 3: Start voice client
cd ../BRAIN
source .venv/bin/activate
python -m brain.voice_client
```

**Usage:**
- Press and hold **SPACE** to record
- Speak your command (e.g., "show me a blue bottle")
- Release **SPACE** to process
- Watch the renderer update

**✓ Test passes when:** Speaking commands updates the 3D renderer in real-time.

---

## Common Commands to Test

Once the full pipeline is running, try:

- "show me a phone prototype"
- "make it red"
- "show me a bottle"
- "zoom in"
- "make it more futuristic"
- "add more bloom"
- "stop rotating"

---

## Architecture

```
Microphone → Audio Capture → Whisper → LLM Parser → WebSocket → Brain → Renderer
   (PTT)      (PyAudio)     (Whisper)  (Claude)    (WS Client)  (Server)  (Three.js)
```

## Files Created

- `brain/audio_capture.py` - Microphone input
- `brain/transcription.py` - Whisper integration
- `brain/llm_parser.py` - Claude API for command extraction
- `brain/ws_client.py` - WebSocket client helper
- `brain/voice_client.py` - Main voice pipeline orchestrator

## Next Steps

After completing all 5 steps:
1. Adjust Whisper model size for speed vs accuracy (`tiny`, `base`, `small`, `medium`, `large`)
2. Tune LLM prompts for better command recognition
3. Add visual feedback for recording state in renderer
4. Consider continuous listening mode vs push-to-talk
