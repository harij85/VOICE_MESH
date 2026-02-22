"""
Whisper transcription module for speech-to-text.
Supports multiple model sizes and languages.
"""
import time
from pathlib import Path
from typing import Optional


class WhisperTranscriber:
    """Transcribes audio using OpenAI Whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model.

        Args:
            model_size: One of ['tiny', 'base', 'small', 'medium', 'large']
                       tiny: fastest, least accurate (~1GB RAM, ~32x realtime)
                       base: good balance (~1GB RAM, ~16x realtime)
                       small: better accuracy (~2GB RAM, ~6x realtime)
                       medium: high accuracy (~5GB RAM, ~2x realtime)
                       large: best accuracy (~10GB RAM, ~1x realtime)
        """
        try:
            import whisper
        except ImportError:
            raise ImportError(
                "Whisper not installed. Install with: pip install openai-whisper"
            )

        # Bypass SSL verification for model download (macOS Python 3.14 issue)
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        print("[whisper] SSL verification bypassed for model download")

        print(f"[whisper] Loading {model_size} model...")
        self.model = whisper.load_model(model_size)
        print(f"[whisper] Model loaded")

    def transcribe(
        self,
        audio_path: Path,
        language: str = "en",
        task: str = "transcribe",
    ) -> dict:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Language code (e.g., 'en', 'es', 'fr')
            task: 'transcribe' or 'translate' (translate always outputs English)

        Returns:
            dict with keys:
                - text: Full transcription
                - segments: List of segments with timestamps
                - language: Detected language
        """
        start = time.time()
        print(f"[whisper] Transcribing {audio_path}...")

        result = self.model.transcribe(
            str(audio_path),
            language=language,
            task=task,
            fp16=False,  # Use FP32 for CPU compatibility
        )

        elapsed = time.time() - start
        print(f"[whisper] Transcription complete in {elapsed:.2f}s")

        return {
            "text": result["text"].strip(),
            "segments": result.get("segments", []),
            "language": result.get("language", language),
        }

    def transcribe_bytes(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str = "en",
    ) -> dict:
        """
        Transcribe audio from raw bytes.

        Args:
            audio_data: Raw audio bytes
            sample_rate: Sample rate of audio
            language: Language code

        Returns:
            Same format as transcribe()
        """
        import numpy as np
        import io
        import wave

        # Convert bytes to temporary WAV file
        temp_path = Path("/tmp/temp_audio.wav")
        with wave.open(str(temp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)

        result = self.transcribe(temp_path, language=language)

        # Clean up temp file
        temp_path.unlink(missing_ok=True)

        return result


def test_transcription():
    """Test function: Transcribe the test recording from Step 1."""
    print("\n=== Step 2: Whisper Transcription Test ===")
    print("This will transcribe the audio file from Step 1.\n")

    # Check if test recording exists
    test_file = Path("test_recording.wav")
    if not test_file.exists():
        print("✗ Test failed! test_recording.wav not found.")
        print("  Please run Step 1 first: python -m brain.audio_capture")
        return

    # Initialize transcriber with 'base' model (good speed/accuracy balance)
    transcriber = WhisperTranscriber(model_size="base")

    # Transcribe
    result = transcriber.transcribe(test_file, language="en")

    # Display results
    print(f"\n✓ Transcription successful!")
    print(f"  Text: '{result['text']}'")
    print(f"  Language: {result['language']}")
    print(f"  Segments: {len(result['segments'])}")

    if result["segments"]:
        print("\n  Detailed segments:")
        for i, seg in enumerate(result["segments"], 1):
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "")
            print(f"    [{start:.2f}s - {end:.2f}s] {text.strip()}")

    # Verify transcription is not empty
    if result["text"]:
        print("\n✓ Test passed! Transcription contains text.")
        print("\nNext step: python -m brain.llm_parser")
    else:
        print("\n✗ Test failed! Transcription is empty.")
        print("  Check that test_recording.wav has audible speech.")


if __name__ == "__main__":
    test_transcription()
