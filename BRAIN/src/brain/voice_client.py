"""
Voice-controlled client for LED Voice Shader.
Orchestrates: Audio Capture → Whisper → LLM → WebSocket
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

try:
    from pynput import keyboard
except ImportError:
    keyboard = None

# Lazy imports to avoid requiring all dependencies upfront
if TYPE_CHECKING:
    from .audio_capture import AudioCapture
    from .transcription import WhisperTranscriber
    from .llm_parser import LLMCommandParser
    from .ws_client import VoiceWebSocketClient


class VoiceClient:
    """Full voice pipeline: speak → transcribe → parse → send."""

    def __init__(
        self,
        whisper_model: str = "base",
        brain_uri: str = "ws://localhost:8765",
        use_llm: bool = True,
    ):
        """
        Initialize voice client.

        Args:
            whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            brain_uri: WebSocket URI for brain server
            use_llm: Use LLM for parsing (True) or regex NLU (False)
        """
        print("[voice] Initializing voice client...")

        # Import modules here to allow graceful error messages
        from .audio_capture import AudioCapture
        from .transcription import WhisperTranscriber
        from .ws_client import VoiceWebSocketClient

        self.audio = AudioCapture(sample_rate=16000)
        self.whisper = WhisperTranscriber(model_size=whisper_model)
        self.ws_client = VoiceWebSocketClient(uri=brain_uri)
        self.use_llm = use_llm

        if use_llm:
            try:
                from .llm_parser import LLMCommandParser
                self.llm = LLMCommandParser()
            except Exception as e:
                print(f"[voice] Failed to initialize LLM: {e}")
                print("[voice] Falling back to regex NLU")
                self.use_llm = False
                self.llm = None
        else:
            self.llm = None

        self.is_recording = False
        self.temp_audio_path = Path("/tmp/voice_command.wav")

        print("[voice] Initialization complete")

    async def process_voice_command(self) -> None:
        """Record, transcribe, parse, and send a voice command."""
        print("\n[voice] 🎤 Recording... (release SPACE to stop)")

        # Start recording
        self.audio.start_recording()
        self.is_recording = True

    async def stop_and_process(self) -> None:
        """Stop recording and process the audio."""
        if not self.is_recording:
            return

        print("[voice] ⏹️  Recording stopped, processing...")
        self.is_recording = False

        # Stop recording and get audio data
        audio_data = self.audio.stop_recording()

        if not audio_data:
            print("[voice] ⚠️  No audio captured")
            return

        # Save to temporary file
        self.audio.save_audio(audio_data, self.temp_audio_path)

        # Transcribe
        print("[voice] 🎧 Transcribing...")
        result = self.whisper.transcribe(self.temp_audio_path)
        text = result["text"]

        if not text:
            print("[voice] ⚠️  No speech detected")
            return

        print(f"[voice] 📝 Transcribed: '{text}'")

        # Parse command
        if self.use_llm:
            print("[voice] 🤖 Parsing with LLM...")
            patch = self.llm.parse(text)
        else:
            print("[voice] 📋 Sending as text command (regex NLU)...")
            patch = None  # Will send as text

        # Send to brain
        try:
            if patch:
                await self.ws_client.send_command_patch(patch)
                print(f"[voice] ✅ Command sent: {patch}")
            else:
                await self.ws_client.send_text_command(text)
                print(f"[voice] ✅ Text sent: '{text}'")

        except Exception as e:
            print(f"[voice] ❌ Failed to send command: {e}")

        # Clean up
        self.temp_audio_path.unlink(missing_ok=True)

        print("[voice] 🎤 Ready for next command (hold SPACE)")

    async def run_with_keyboard(self) -> None:
        """Run voice client with keyboard (SPACE) for push-to-talk."""
        if keyboard is None:
            print("[voice] Error: pynput not installed")
            print("  Install: pip install pynput")
            return

        print("\n" + "=" * 60)
        print("LED VOICE SHADER - Voice Control")
        print("=" * 60)
        print("\nControls:")
        print("  SPACE (hold): Record voice command")
        print("  SPACE (release): Process and send command")
        print("  Ctrl+C: Exit")
        print("\n" + "=" * 60)

        # Connect to brain
        await self.ws_client.connect()

        # BUG-010 FIX: pynput keyboard callbacks run in a separate OS thread.
        # asyncio.create_task() requires the caller to be on the event loop thread,
        # so calling it from a pynput callback raises RuntimeError at runtime.
        # Use asyncio.run_coroutine_threadsafe() instead, which is thread-safe.
        loop = asyncio.get_event_loop()

        def on_press(key):
            if key == keyboard.Key.space and not self.is_recording:
                asyncio.run_coroutine_threadsafe(self.process_voice_command(), loop)

        def on_release(key):
            if key == keyboard.Key.space and self.is_recording:
                asyncio.run_coroutine_threadsafe(self.stop_and_process(), loop)
            elif key == keyboard.Key.esc:
                return False  # Stop listener

        # Start keyboard listener in background
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        print("\n[voice] 🎤 Ready! Hold SPACE to record...\n")

        try:
            # Keep running
            while listener.running:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[voice] Shutting down...")
        finally:
            listener.stop()
            await self.ws_client.disconnect()
            self.audio.cleanup()

    async def run_simple(self) -> None:
        """Simple mode: press Enter to record, automatic stop after 3 seconds."""
        print("\n" + "=" * 60)
        print("LED VOICE SHADER - Voice Control (Simple Mode)")
        print("=" * 60)
        print("\nControls:")
        print("  Press ENTER: Record 3-second voice command")
        print("  Ctrl+C: Exit")
        print("\n" + "=" * 60)

        # Connect to brain
        await self.ws_client.connect()

        print("\n[voice] Ready! Press ENTER to record...\n")

        try:
            while True:
                # Wait for Enter
                await asyncio.get_event_loop().run_in_executor(None, input, "")

                print("[voice] 🎤 Recording 3 seconds...")
                self.is_recording = True  # Set flag so stop_and_process() works
                self.audio.start_recording()
                await asyncio.sleep(3)

                # Process
                await self.stop_and_process()

        except KeyboardInterrupt:
            print("\n[voice] Shutting down...")
        finally:
            await self.ws_client.disconnect()
            self.audio.cleanup()


async def main():
    """Run the voice client."""
    import argparse

    parser = argparse.ArgumentParser(description="Voice-controlled LED Voice Shader")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use regex NLU instead of LLM parsing",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Simple mode (Enter to record, no keyboard lib needed)",
    )
    parser.add_argument(
        "--uri",
        default="ws://localhost:8765",
        help="Brain WebSocket URI (default: ws://localhost:8765)",
    )

    args = parser.parse_args()

    client = VoiceClient(
        whisper_model=args.model,
        brain_uri=args.uri,
        use_llm=not args.no_llm,
    )

    if args.simple or keyboard is None:
        await client.run_simple()
    else:
        await client.run_with_keyboard()


def cli() -> None:
    """Entry point for the voice command (synchronous wrapper)."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
