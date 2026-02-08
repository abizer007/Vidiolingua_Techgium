"""
VidioLingua Backend API - FastAPI app.
"""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from backend import job_store

# Base directory for job workspaces (relative to project root when running uvicorn from root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
JOBS_DIR = Path(os.environ.get("JOBS_DIR", str(PROJECT_ROOT / "jobs")))

app = FastAPI(title="VidioLingua API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/deps")
def health_deps():
    """Check that required tools and packages are available for the pipeline."""
    import shutil
    out = {
        "ffmpeg": False,
        "gtts": False,
        "faster_whisper": False,
        "deep_translator": False,
        "elevenlabs_api_key": False,
        "wav2lip": False,
        "ready": False,
    }
    out["ffmpeg"] = bool(shutil.which("ffmpeg"))
    try:
        __import__("gtts")
        out["gtts"] = True
    except ImportError:
        pass
    try:
        __import__("faster_whisper")
        out["faster_whisper"] = True
    except ImportError:
        pass
    try:
        __import__("deep_translator")
        out["deep_translator"] = True
    except ImportError:
        pass
    out["elevenlabs_api_key"] = bool(
        os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("VIDIOLINGUA_ELEVENLABS_API_KEY")
    )
    wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
    wav2lip_checkpoint = os.environ.get("VIDIOLINGUA_WAV2LIP_CHECKPOINT", "")
    if wav2lip_dir:
        wav2lip_path = Path(wav2lip_dir) / "inference.py"
        out["wav2lip"] = wav2lip_path.exists() and (not wav2lip_checkpoint or Path(wav2lip_checkpoint).exists())
    out["ready"] = (
        out["ffmpeg"] and out["gtts"] and out["faster_whisper"] and out["deep_translator"]
    )
    return out


@app.post("/api/upload")
async def upload(
    video: UploadFile = File(...),
    languages: str = Form("[]"),
    voiceOptions: str = Form("{}"),
    sourceLanguage: str = Form(""),
    voiceSample: UploadFile | None = File(None),
):
    """Accept video upload, create job, save file, return jobId. Start pipeline in background."""
    import json
    from backend.pipeline_runner import run_pipeline_background

    # Validate video type
    if not video.filename or not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(400, "A video file is required")

    try:
        lang_list = json.loads(languages)
    except json.JSONDecodeError:
        lang_list = ["hi", "es", "fr", "de", "ja", "zh", "ar", "pt"]

    supported = {"hi", "es", "fr", "de", "ja", "zh", "ar", "pt"}
    code_map = {
        "Hindi": "hi",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Japanese": "ja",
        "Chinese": "zh",
        "Arabic": "ar",
        "Portuguese": "pt",
        "hi": "hi",
        "es": "es",
        "fr": "fr",
        "de": "de",
        "ja": "ja",
        "zh": "zh",
        "ar": "ar",
        "pt": "pt",
    }
    lang_codes = [code_map.get(str(x), x) if isinstance(x, str) else x for x in lang_list]
    lang_codes = [c for c in lang_codes if c in supported] or list(supported)

    # Parse voice options
    try:
        voice_opts = json.loads(voiceOptions)
    except json.JSONDecodeError:
        voice_opts = {}

    source_lang = sourceLanguage.strip().lower()
    if source_lang == "auto" or not source_lang:
        source_lang = ""

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded video with a stable name (e.g. input.mp4)
    video_path = job_dir / "input_video.mp4"
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    voice_sample_path = None
    if voiceSample is not None and voiceSample.filename:
        sample_path = job_dir / "voice_sample.wav"
        with open(sample_path, "wb") as f:
            content = await voiceSample.read()
            f.write(content)
        voice_sample_path = str(sample_path)

    job_store.create_job(
        job_id,
        str(video_path),
        lang_codes,
        source_language=source_lang or None,
        voice_options=voice_opts,
        voice_sample_path=voice_sample_path,
    )
    run_pipeline_background(
        job_id,
        str(video_path),
        lang_codes,
        source_language=source_lang or None,
        voice_options=voice_opts,
        voice_sample_path=voice_sample_path,
    )
    return {"jobId": job_id}


@app.get("/api/job-status/{job_id}")
def job_status(job_id: str):
    """Return job status for polling."""
    data = job_store.get_job_status_response(job_id)
    if data is None:
        raise HTTPException(404, "Job not found")
    return data


@app.get("/api/result/{job_id}")
def result(job_id: str):
    """Return processing result when job is complete (or error)."""
    data = job_store.get_job_result_response(job_id)
    if data is None:
        # Job still running or not found
        job = job_store.get_job(job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        raise HTTPException(202, "Job not complete")
    return data


@app.get("/api/result/{job_id}/file/{filename:path}")
def result_file(job_id: str, filename: str):
    """Serve a file from the job's results directory. Safe filename only (no path traversal)."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    job_dir = JOBS_DIR / job_id
    results_dir = job_dir / "results"
    file_path = (results_dir / filename).resolve()
    results_resolved = results_dir.resolve()
    if not str(file_path).startswith(str(results_resolved) + os.sep) and file_path != results_resolved:
        raise HTTPException(400, "Invalid filename")
    if not file_path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(file_path, filename=Path(filename).name)
