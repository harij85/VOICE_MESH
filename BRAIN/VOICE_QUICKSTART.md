# Voice Pipeline Quick Start

This is a condensed version of the full setup guide. Use this if you want to get voice control working quickly.

## Prerequisites

```bash
cd BRAIN
source .venv/bin/activate
pip install -e ".[voice]"
```

Create `.env` file in `BRAIN/` directory:
```
ANTHROPIC_API_KEY=your_key_here
```

Get API key from: https://console.anthropic.com/

## Quick Test (All-in-One)

**Terminal 1 - Start Brain:**
```bash
brain
```

**Terminal 2 - Start Renderer:**
```bash
cd ../renderer
npm run dev
```

**Terminal 3 - Start Voice Control:**
```bash
cd ../BRAIN
source .venv/bin/activate
voice
```

**Usage:**
- Hold **SPACE** to record
- Speak a command (e.g., "show me a blue bottle")
- Release **SPACE** to process
- Watch the renderer update

## Troubleshooting

### PyAudio won't install
- macOS: `brew install portaudio`
- Linux: `sudo apt-get install portaudio19-dev`
- Windows: Should work with `pip install pyaudio`

### No microphone detected
- Check system permissions (microphone access)
- Run `python -m brain.audio_capture` to list devices

### Whisper is slow
Use a smaller model:
```bash
voice --model tiny  # Fastest, less accurate
voice --model base  # Good balance (default)
voice --model small # Better accuracy, slower
```

### LLM parsing fails
Fall back to regex NLU:
```bash
voice --no-llm
```

### Keyboard library not working
Use simple mode:
```bash
voice --simple  # Press Enter instead of Space
```

## Common Voice Commands

Try these once voice control is running:

**Objects:**
- "show me a phone"
- "show me a bottle"
- "show me a headset"

**Colors:**
- "make it red"
- "make it electric blue"
- "change color to green"

**Camera:**
- "zoom in"
- "zoom out"
- "stop rotating"
- "start rotating"

**Effects:**
- "make it more futuristic"
- "add more bloom"
- "make it glossy"
- "fade out"

## Architecture

```
You speak → Microphone → Whisper → LLM → WebSocket → Brain → Renderer
             (PyAudio)   (base)   (Claude)  (patch)    (state)  (Three.js)
```

## Next Steps

- Fine-tune LLM prompts in `llm_parser.py`
- Adjust Whisper model size for your hardware
- Add custom voice commands
- Implement continuous listening mode
