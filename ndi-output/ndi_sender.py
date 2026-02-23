#!/usr/bin/env python3
"""
NDI sender subprocess for VOICE_MESH.

Reads raw RGBA frames (1920x1080x4 = 8,294,400 bytes each) from stdin
and sends them as NDI video frames using cyndilib.

Usage:
    python ndi_sender.py [--name VOICE_MESH] [--width 1920] [--height 1080]

Requires:
    pip install cyndilib numpy
"""

import sys
import argparse
from fractions import Fraction

import numpy as np

try:
    from cyndilib.sender import Sender
    from cyndilib.video_frame import VideoSendFrame
    from cyndilib.wrapper.ndi_structs import FourCC
except ImportError:
    print(
        "[NDI] ERROR: cyndilib not installed.\n"
        "  Install with: pip install cyndilib\n"
        "  Also install NDI runtime from https://ndi.video/tools/",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="VOICE_MESH NDI sender")
    parser.add_argument("--name", default="VOICE_MESH", help="NDI source name")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()

    frame_size = args.width * args.height * 4  # RGBA

    sender = Sender(args.name)
    video_frame = VideoSendFrame()
    video_frame.set_resolution(args.width, args.height)
    video_frame.set_fourcc(FourCC.RGBA)
    video_frame.set_frame_rate(Fraction(30000, 1001))

    sender.set_video_frame(video_frame)
    sender.open()

    print(f"[NDI] Sender '{args.name}' opened ({args.width}x{args.height} RGBA)", file=sys.stderr)

    frames_sent = 0
    stdin = sys.stdin.buffer
    # Pre-allocate a writable buffer for pixel data (cyndilib requires writable arrays)
    pixel_buf = np.zeros(frame_size, dtype=np.uint8)

    try:
        while True:
            # Read exactly one frame of RGBA data
            data = b""
            while len(data) < frame_size:
                chunk = stdin.read(frame_size - len(data))
                if not chunk:
                    # EOF — parent process closed the pipe
                    print(f"\n[NDI] EOF after {frames_sent} frames. Shutting down.", file=sys.stderr)
                    return
                data += chunk

            # Copy into writable numpy array and send
            pixel_buf[:] = np.frombuffer(data, dtype=np.uint8)
            video_frame.write_data(pixel_buf)
            sender.send_video()

            frames_sent += 1
            if frames_sent % 300 == 0:
                print(f"[NDI] {frames_sent} frames sent", file=sys.stderr)

    except KeyboardInterrupt:
        print(f"\n[NDI] Interrupted after {frames_sent} frames.", file=sys.stderr)
    finally:
        sender.close()
        print("[NDI] Sender closed.", file=sys.stderr)


if __name__ == "__main__":
    main()
