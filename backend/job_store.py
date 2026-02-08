"""
In-memory job store for VidioLingua pipeline jobs.
Maps jobId -> status, progress, result paths, error.
"""

from typing import Any, Optional
import threading

# Pipeline stages matching frontend-next types
STAGES = ["uploading", "asr", "translation", "tts", "lipsync", "complete", "error"]

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def create_job(
    job_id: str,
    video_path: str,
    languages: list[str],
    source_language: Optional[str] = None,
    voice_options: Optional[dict] = None,
    voice_sample_path: Optional[str] = None,
) -> None:
    with _lock:
        _jobs[job_id] = {
            "jobId": job_id,
            "stage": "uploading",
            "progress": 0,
            "currentLanguage": None,
            "languages": languages,
            "sourceLanguage": source_language,
            "sourceLanguageConfidence": None,
            "voiceOptions": voice_options or {},
            "voiceSamplePath": voice_sample_path,
            "error": None,
            "metrics": {},
            "video_path": video_path,
            "result": None,
            "started_at": None,
        }


def update_job(
    job_id: str,
    stage: Optional[str] = None,
    progress: Optional[int] = None,
    current_language: Optional[str] = None,
    source_language: Optional[str] = None,
    source_language_confidence: Optional[float] = None,
    error: Optional[str] = None,
    metrics: Optional[dict] = None,
    result: Optional[dict] = None,
    voice_options: Optional[dict] = None,
    voice_sample_path: Optional[str] = None,
) -> None:
    with _lock:
        if job_id not in _jobs:
            return
        j = _jobs[job_id]
        if stage is not None:
            j["stage"] = stage
        if progress is not None:
            j["progress"] = min(100, max(0, progress))
        if current_language is not None:
            j["currentLanguage"] = current_language
        if source_language is not None:
            j["sourceLanguage"] = source_language
        if source_language_confidence is not None:
            j["sourceLanguageConfidence"] = source_language_confidence
        if error is not None:
            j["error"] = error
            j["stage"] = "error"
        if metrics is not None:
            j["metrics"] = {**j.get("metrics", {}), **metrics}
        if voice_options is not None:
            j["voiceOptions"] = voice_options
        if voice_sample_path is not None:
            j["voiceSamplePath"] = voice_sample_path
        if result is not None:
            j["result"] = result


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    with _lock:
        return _jobs.get(job_id)


def get_job_status_response(job_id: str) -> Optional[dict]:
    """Return job data in the shape expected by frontend GET /api/job-status/:jobId"""
    with _lock:
        if job_id not in _jobs:
            return None
        j = _jobs[job_id]
        return {
            "jobId": j["jobId"],
            "stage": j["stage"],
            "progress": j["progress"],
            "currentLanguage": j.get("currentLanguage"),
            "languages": j.get("languages", []),
            "sourceLanguage": j.get("sourceLanguage"),
            "sourceLanguageConfidence": j.get("sourceLanguageConfidence"),
            "error": j.get("error"),
            "metrics": j.get("metrics") or {},
        }


def get_job_result_response(job_id: str) -> Optional[dict]:
    """Return job result in the shape expected by frontend GET /api/result/:jobId"""
    with _lock:
        if job_id not in _jobs:
            return None
        j = _jobs[job_id]
        if j.get("result") is not None:
            return j["result"]
        if j.get("stage") == "error":
            return {
                "jobId": job_id,
                "originalVideo": "",
                "localizedVideos": [],
                "metrics": {"totalTime": 0, "languagesProcessed": 0},
                "error": j.get("error"),
            }
        return None
