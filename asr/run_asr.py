"""
Automatic Speech Recognition (ASR) Module

Transcribes video files using Whisper (faster-whisper).
Extracts audio with ffmpeg, then transcribes full content with timestamps.
"""

import json
import subprocess
import tempfile
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"

# Whisper model size: "tiny" (fast, less accurate), "base", "small", "medium", "large-v3"
WHISPER_MODEL = "base"


def extract_audio_ffmpeg(video_path: Path, output_wav: Path) -> None:
    """Extract 16kHz mono WAV for Whisper using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output_wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg extract failed: {r.stderr or r.stdout}")


def process_video(video_path: Path) -> dict:
    """
    Transcribe video: extract audio, run Whisper, return segments with timestamps.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "ASR requires faster-whisper. Install with: pip install faster-whisper"
        ) from e

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = Path(tmp.name)
    try:
        extract_audio_ffmpeg(video_path, audio_path)
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        segments_gen, info = model.transcribe(str(audio_path), language="en", beam_size=1)
        segments_list = []
        for s in segments_gen:
            text = (s.text or "").strip()
            if text:
                segments_list.append({
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "text": text,
                })
        if not segments_list:
            segments_list = [{"start": 0.0, "end": 0.1, "text": "(no speech detected)"}]
        return {
            "video_file": str(video_path),
            "segments": segments_list,
            "language": info.language or "en",
        }
    finally:
        audio_path.unlink(missing_ok=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_files = (
        list(INPUT_DIR.glob("*.mp4"))
        + list(INPUT_DIR.glob("*.avi"))
        + list(INPUT_DIR.glob("*.mov"))
    )
    if not video_files:
        print(f"No video files found in {INPUT_DIR}")
        return
    for video_file in video_files:
        print(f"Processing: {video_file.name}")
        transcription = process_video(video_file)
        output_file = OUTPUT_DIR / f"{video_file.stem}_transcription.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transcription, f, indent=2, ensure_ascii=False)
        print(f"Transcription saved to: {output_file} ({len(transcription['segments'])} segments)")


if __name__ == "__main__":
    main()
