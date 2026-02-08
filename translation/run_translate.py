"""
Machine Translation (MT) Module

Translates transcription segments using Google Translate via deep-translator (no API key).
"""

import os
import json
import time
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"

_default = ["hi", "es", "fr", "de", "ja", "zh", "ar", "pt"]
TARGET_LANGUAGES = (
    os.environ.get("VIDIOLINGUA_TARGET_LANGUAGES", "").strip().split(",") or _default
)
TARGET_LANGUAGES = [x.strip() for x in TARGET_LANGUAGES if x.strip()] or _default


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate a single segment using Google Translate (deep-translator)."""
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
    except ImportError as e:
        raise RuntimeError(
            "Translation requires deep-translator. Install with: pip install deep-translator"
        ) from e
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        out = translator.translate(text=text)
        return out or text
    except Exception as e:
        print(f"Translation warning ({source_lang}->{target_lang}): {e}")
        return text


def translate_transcription(transcription_data: dict, target_lang: str) -> dict:
    """Translate all segments to the target language. Keeps timestamps."""
    translated = {
        "video_file": transcription_data.get("video_file", ""),
        "segments": [],
        "language": target_lang,
    }
    source_lang = transcription_data.get("language", "en")
    for seg in transcription_data.get("segments", []):
        if source_lang == target_lang:
            translated_text = seg.get("text", "")
        else:
            translated_text = translate_text(seg.get("text", ""), source_lang, target_lang)
        translated["segments"].append({
            "start": seg["start"],
            "end": seg["end"],
            "text": translated_text,
        })
        time.sleep(0.05)  # avoid rate limiting
    return translated


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    transcription_files = list(INPUT_DIR.glob("*_transcription.json"))
    if not transcription_files:
        print(f"No transcription files found in {INPUT_DIR}")
        return
    for transcription_file in transcription_files:
        print(f"Processing: {transcription_file.name}")
        with open(transcription_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for target_lang in TARGET_LANGUAGES:
            translated = translate_transcription(data, target_lang)
            output_file = OUTPUT_DIR / f"{transcription_file.stem}_{target_lang}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(translated, f, indent=2, ensure_ascii=False)
            print(f"Translation saved to: {output_file}")


if __name__ == "__main__":
    main()
