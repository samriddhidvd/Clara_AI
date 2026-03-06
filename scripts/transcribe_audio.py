#!/usr/bin/env python3
"""
Clara AI - Local Audio Transcription
------------------------------------
Leverages OpenAI's Whisper model to perform zero-cost, private transcription 
of meeting recordings (.mp4, .m4a, .mp3). 

Author: Clara AI Pipeline Team
"""

import os
import sys
import logging

# Production-grade logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("clara.transcribe")

def transcribe(audio_path: str, output_txt: str = None, model_size: str = "base"):
    try:
        import whisper
    except ImportError:
        log.error("Whisper not installed. Run: pip install openai-whisper")
        sys.exit(1)

    if not os.path.exists(audio_path):
        log.error(f"Audio file not found: {audio_path}")
        sys.exit(1)

    if output_txt is None:
        base = os.path.splitext(audio_path)[0]
        output_txt = base + "_transcript.txt"

    log.info(f"Loading Whisper '{model_size}' model (first run downloads ~145MB)...")
    model = whisper.load_model(model_size)

    log.info(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path, verbose=False)

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(result["text"])

    log.info(f"Transcript saved → {output_txt}")
    return output_txt

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe_audio.py <audio_file> [output_txt] [model_size]")
        print("  audio_file  : path to .mp4, .m4a, or .mp3")
        print("  output_txt  : optional output path (default: same dir as audio)")
        print("  model_size  : tiny | base | small | medium (default: base)")
        sys.exit(1)
    audio = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    size = sys.argv[3] if len(sys.argv) > 3 else "base"
    transcribe(audio, out, size)
