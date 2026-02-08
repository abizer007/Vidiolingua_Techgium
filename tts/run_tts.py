"""
Text-to-Speech (TTS) Module

Reads translated transcription files and generates WAV audio using gTTS + ffmpeg.
Uses gTTS for MP3, then ffmpeg to convert to WAV (no pydub; works on Python 3.13+).
"""

import json
import subprocess
import tempfile
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def synthesize_speech(text, language_code, output_path):
    """
    Synthesize speech from text using gTTS (MP3), then convert to WAV via ffmpeg.
    """
    if not text or not text.strip():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"")
        return output_path

    try:
        from gtts import gTTS
    except ImportError as e:
        raise RuntimeError(
            "TTS requires gTTS. Install with: pip install gTTS. "
            "Also ensure ffmpeg is on PATH."
        ) from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_path = tmp.name
    try:
        tts = gTTS(text=text, lang=language_code, slow=False)
        tts.save(mp3_path)
        # Convert MP3 to WAV using ffmpeg (no pydub = no audioop on Python 3.13)
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-acodec", "pcm_s16le", "-ar", "22050", str(output_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {r.stderr or r.stdout or r.returncode}")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Install ffmpeg and add it to PATH.") from None
    except Exception as e:
        raise RuntimeError(f"TTS synthesis failed: {e}") from e
    finally:
        Path(mp3_path).unlink(missing_ok=True)
    return output_path


# gTTS has ~5000 char limit; chunk to avoid failure on long videos
MAX_CHARS_PER_CHUNK = 4000


def _chunk_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text] if text.strip() else []
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text.strip())
            break
        idx = text.rfind(" ", 0, max_len + 1)
        if idx <= 0:
            idx = max_len
        chunks.append(text[:idx].strip())
        text = text[idx:].strip()
    return [c for c in chunks if c]


def generate_audio_from_transcription(transcription_data, output_path):
    language_code = transcription_data.get("language", "en")
    full_text = " ".join(
        segment["text"] for segment in transcription_data.get("segments", [])
    )
    if not full_text.strip():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"")
        return output_path
    chunks = _chunk_text(full_text, MAX_CHARS_PER_CHUNK)
    if len(chunks) == 1:
        return synthesize_speech(chunks[0], language_code, output_path)
    # Multiple chunks: generate each, then concat with ffmpeg
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wavs = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for i, chunk in enumerate(chunks):
            wav = tmp / f"chunk_{i}.wav"
            synthesize_speech(chunk, language_code, wav)
            wavs.append(wav)
        # Concat using ffmpeg concat demuxer (paths with forward slashes for compatibility)
        concat_list = tmp / "concat.txt"
        concat_list.write_text("\n".join(f"file '{w.resolve().as_posix()}'" for w in wavs))
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(output_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {r.stderr or r.stdout}")
    return output_path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    transcription_files = list(INPUT_DIR.glob("*_transcription_*.json"))

    if not transcription_files:
        print(f"No translated transcription files found in {INPUT_DIR}")
        return

    for transcription_file in transcription_files:
        print(f"Processing: {transcription_file.name}")
        with open(transcription_file, "r", encoding="utf-8") as f:
            transcription_data = json.load(f)
        output_file = OUTPUT_DIR / f"{transcription_file.stem}.wav"
        generate_audio_from_transcription(transcription_data, output_file)
        print(f"Audio saved to: {output_file}")


if __name__ == "__main__":
    main()
