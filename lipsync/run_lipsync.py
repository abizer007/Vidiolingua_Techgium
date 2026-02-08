"""
Lip Synchronization Module

Combines the original video with generated audio to create dubbed videos.
Uses ffmpeg for audio replacement (no lip re-sync in this minimal demo).
Requires ffmpeg on PATH.
"""

import os
import subprocess
import sys
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def replace_audio_with_ffmpeg(video_path, audio_path, output_path):
    """
    Replace video's audio track with the given audio file using ffmpeg.

    Args:
        video_path: Path to the original video file
        audio_path: Path to the audio file (WAV/MP3)
        output_path: Path to save the output video

    Returns:
        Path: Path to the generated video file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr or result.stdout}")
    return output_path


def run_wav2lip(video_path: Path, audio_path: Path, output_path: Path) -> None:
    wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
    if not wav2lip_dir:
        raise RuntimeError("VIDIOLINGUA_WAV2LIP_DIR is not set")
    wav2lip_dir = Path(wav2lip_dir)
    inference_script = wav2lip_dir / "inference.py"
    checkpoint = os.environ.get("VIDIOLINGUA_WAV2LIP_CHECKPOINT", str(wav2lip_dir / "checkpoints" / "wav2lip_gan.pth"))
    if not inference_script.exists():
        raise RuntimeError("Wav2Lip inference.py not found")
    cmd = [
        os.environ.get("PYTHON", "python"),
        str(inference_script),
        "--checkpoint_path",
        checkpoint,
        "--face",
        str(video_path),
        "--audio",
        str(audio_path),
        "--outfile",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Wav2Lip failed: {result.stderr or result.stdout}")


def main():
    """Main entry point for lip synchronization processing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_files = (
        list(INPUT_DIR.glob("*.mp4"))
        + list(INPUT_DIR.glob("*.avi"))
        + list(INPUT_DIR.glob("*.mov"))
    )
    audio_files = list(INPUT_DIR.glob("*.wav")) + list(INPUT_DIR.glob("*.mp3"))

    if not video_files:
        print(f"No video files found in {INPUT_DIR}")
        return
    if not audio_files:
        print(f"No audio files found in {INPUT_DIR}")
        return

    original_video = video_files[0]
    print(f"Using original video: {original_video.name}")

    had_error = False
    for audio_file in audio_files:
        print(f"Processing audio: {audio_file.name}")
        language_code = audio_file.stem.split("_")[-1]
        output_file = OUTPUT_DIR / f"{original_video.stem}_dubbed_{language_code}.mp4"
        try:
            if os.environ.get("VIDIOLINGUA_WAV2LIP_DIR"):
                run_wav2lip(original_video, audio_file, output_file)
            else:
                replace_audio_with_ffmpeg(original_video, audio_file, output_file)
            print(f"Dubbed video saved to: {output_file}")
        except Exception as e:
            print(f"Error processing {audio_file.name}: {e}", file=sys.stderr)
            had_error = True
    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
