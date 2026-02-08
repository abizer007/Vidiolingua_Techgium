"""
Text-to-Speech (TTS) Module

Reads translated transcription files and generates WAV audio using gTTS + ffmpeg.
Uses gTTS for MP3, then ffmpeg to convert to WAV (no pydub; works on Python 3.13+).
"""

import json
import os
import subprocess
import tempfile
from typing import Optional
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def _ffmpeg_convert_to_wav(mp3_path: str, output_path: Path) -> None:
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(output_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr or r.stdout or r.returncode}")


def _get_voice_settings(voice_options: dict) -> dict:
    gender = (voice_options or {}).get("gender", "neutral")
    emotion = (voice_options or {}).get("emotion", "neutral")
    style = 0.2
    if emotion == "happy":
        style = 0.5
    elif emotion == "sad":
        style = 0.15
    elif emotion == "excited":
        style = 0.7
    stability = 0.4 if gender == "male" else 0.35 if gender == "female" else 0.3
    similarity = 0.75
    return {
        "stability": stability,
        "similarity_boost": similarity,
        "style": style,
        "use_speaker_boost": True,
    }


def _elevenlabs_request(api_key: str, method: str, url: str, **kwargs):
    import requests
    headers = kwargs.pop("headers", {})
    headers["xi-api-key"] = api_key
    headers["accept"] = "application/json"
    return requests.request(method, url, headers=headers, timeout=120, **kwargs)


def _create_elevenlabs_voice(api_key: str, sample_path: str, name: str) -> str:
    url = "https://api.elevenlabs.io/v1/voices/add"
    with open(sample_path, "rb") as f:
        files = {"files": f}
        data = {"name": name, "description": "VidioLingua auto-cloned voice"}
        resp = _elevenlabs_request(api_key, "POST", url, files=files, data=data)
    if resp.status_code >= 300:
        raise RuntimeError(f"ElevenLabs voice create failed: {resp.text}")
    return resp.json().get("voice_id")


def _elevenlabs_tts(
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str,
    output_mp3_path: str,
    voice_settings: dict,
) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }
    resp = _elevenlabs_request(api_key, "POST", url, json=payload, headers={"accept": "audio/mpeg"})
    if resp.status_code >= 300:
        raise RuntimeError(f"ElevenLabs TTS failed: {resp.text}")
    with open(output_mp3_path, "wb") as f:
        f.write(resp.content)


def synthesize_speech(text, language_code, output_path, voice_options=None, voice_id: Optional[str] = None):
    """
    Synthesize speech with ElevenLabs (preferred) or gTTS fallback, then convert to WAV via ffmpeg.
    """
    if not text or not text.strip():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_path = tmp.name
    try:
        api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("VIDIOLINGUA_ELEVENLABS_API_KEY")
        model_id = os.environ.get("VIDIOLINGUA_ELEVENLABS_MODEL", "eleven_multilingual_v2")
        if api_key and voice_id:
            settings = _get_voice_settings(voice_options or {})
            _elevenlabs_tts(api_key, voice_id, text, model_id, mp3_path, settings)
        else:
            try:
                from gtts import gTTS
            except ImportError as e:
                raise RuntimeError(
                    "TTS requires gTTS or ElevenLabs. Install with: pip install gTTS. "
                    "Also ensure ffmpeg is on PATH."
                ) from e
            tts = gTTS(text=text, lang=language_code, slow=False)
            tts.save(mp3_path)
        _ffmpeg_convert_to_wav(mp3_path, output_path)
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


def generate_audio_from_transcription(transcription_data, output_path, voice_options=None, voice_id: Optional[str] = None):
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
        return synthesize_speech(chunks[0], language_code, output_path, voice_options, voice_id)
    # Multiple chunks: generate each, then concat with ffmpeg
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wavs = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for i, chunk in enumerate(chunks):
            wav = tmp / f"chunk_{i}.wav"
            synthesize_speech(chunk, language_code, wav, voice_options, voice_id)
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

    voice_options = {}
    try:
        voice_options = json.loads(os.environ.get("VIDIOLINGUA_VOICE_OPTIONS", "{}"))
    except json.JSONDecodeError:
        voice_options = {}
    use_cloned = bool(voice_options.get("cloned"))
    voice_sample = os.environ.get("VIDIOLINGUA_VOICE_SAMPLE", "").strip()
    api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("VIDIOLINGUA_ELEVENLABS_API_KEY")
    default_voice_id = os.environ.get("ELEVENLABS_VOICE_ID") or os.environ.get("VIDIOLINGUA_ELEVENLABS_VOICE_ID")
    voice_id = default_voice_id
    if api_key and use_cloned and voice_sample:
        try:
            voice_id = _create_elevenlabs_voice(api_key, voice_sample, f"vidiolingua_{Path(voice_sample).stem}")
        except Exception as e:
            print(f"Voice cloning unavailable, falling back to default voice: {e}")

    for transcription_file in transcription_files:
        print(f"Processing: {transcription_file.name}")
        with open(transcription_file, "r", encoding="utf-8") as f:
            transcription_data = json.load(f)
        output_file = OUTPUT_DIR / f"{transcription_file.stem}.wav"
        generate_audio_from_transcription(transcription_data, output_file, voice_options, voice_id)
        print(f"Audio saved to: {output_file}")


if __name__ == "__main__":
    main()
