"""
Audio capture module for microphone input.
Supports push-to-talk and continuous recording modes.
"""
import pyaudio
import wave
import threading
from pathlib import Path
from typing import Optional, Callable


class AudioCapture:
    """Captures audio from microphone with push-to-talk support."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        format: int = pyaudio.paInt16,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = format

        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.frames: list[bytes] = []
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None

    def list_devices(self) -> list[dict]:
        """List all available audio input devices."""
        devices = []
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append(
                    {
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxInputChannels"],
                        "sample_rate": int(info["defaultSampleRate"]),
                    }
                )
        return devices

    def start_recording(self, device_index: Optional[int] = None) -> None:
        """Start recording audio from microphone."""
        if self.is_recording:
            print("[audio] Already recording")
            return

        self.frames = []
        self.is_recording = True

        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size,
        )

        def record():
            print("[audio] Recording started...")
            while self.is_recording:
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.frames.append(data)
                except Exception as e:
                    print(f"[audio] Error reading stream: {e}")
                    break

        self.recording_thread = threading.Thread(target=record, daemon=True)
        self.recording_thread.start()

    def stop_recording(self) -> bytes:
        """Stop recording and return audio data."""
        if not self.is_recording:
            print("[audio] Not currently recording")
            return b""

        self.is_recording = False

        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        print(f"[audio] Recording stopped. Captured {len(self.frames)} chunks")

        # Combine all frames into single bytes object
        return b"".join(self.frames)

    def save_audio(self, audio_data: bytes, filepath: Path) -> None:
        """Save audio data to WAV file."""
        with wave.open(str(filepath), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)
        print(f"[audio] Saved to {filepath}")

    def cleanup(self) -> None:
        """Release audio resources."""
        if self.is_recording:
            self.stop_recording()
        self.audio.terminate()


def test_audio_capture():
    """Test function: Record 3 seconds of audio and save to file."""
    import time

    print("\n=== Step 1: Audio Capture Test ===")
    print("This will record 3 seconds of audio from your microphone.\n")

    capture = AudioCapture()

    # List available devices
    devices = capture.list_devices()
    print("Available audio input devices:")
    for dev in devices:
        print(f"  [{dev['index']}] {dev['name']} ({dev['channels']} ch, {dev['sample_rate']} Hz)")

    # Start recording
    print("\nRecording will start in 1 second...")
    time.sleep(1)

    capture.start_recording()
    time.sleep(3)  # Record for 3 seconds

    # Stop and save
    audio_data = capture.stop_recording()

    if audio_data:
        output_path = Path("test_recording.wav")
        capture.save_audio(audio_data, output_path)
        print(f"\n✓ Test passed! Audio saved to {output_path}")
        print(f"  File size: {len(audio_data)} bytes")
        print("\nPlay the file to verify recording worked.")
    else:
        print("\n✗ Test failed! No audio data captured.")

    capture.cleanup()


if __name__ == "__main__":
    test_audio_capture()
