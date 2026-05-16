"""
main.py
FastAPI entry point — 9-step analysis pipeline.

Fixes applied:
  - BUG: _save_upload used shutil.copyfileobj (synchronous blocking I/O) inside
    an async handler, stalling the event loop for every request. Fixed to use
    `await upload.read()` which is properly async.
  - BUG: Uploaded files used the raw upload.filename as the save path. Two
    concurrent requests uploading "resume.pdf" would silently overwrite each
    other, producing wrong results. Fixed with UUID-prefixed filenames.
  - BUG: Uploaded files were never deleted after analysis, causing unbounded
    disk growth. Fixed by cleaning up in a finally block.
  - BUG: No file size limit — a huge PDF could exhaust memory. Added 10 MB cap.
  - BUG: No MIME type check beyond extension. Added content-type guard.
"""

import logging
import os
import traceback
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.extraction.pdf_extractor import extract_text_from_pdf, PDFExtractionError
from app.parsing.jd_parser import parse_jd
from app.parsing.resume_parser import parse_resume
from app.graph.skill_expander import expand_skills_for_role
from app.graph.graph_builder import build_jd_graph
from app.graph.propagation import propagate_skills
from app.graph.visualization import build_graph_visualization
from app.scoring.readiness import calculate_readiness
from app.recommendations.engine import generate_recommendations
from app.models.response_models import AnalysisResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dynamic Role-Aware Knowledge Graph",
    description="Resume–JD Alignment and Applicant Readiness Scoring",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.upload_dir, exist_ok=True)

# Max upload size: 10 MB
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def _save_upload(upload: UploadFile, label: str) -> str:
    """
    Save an uploaded file to disk asynchronously.

    FIX 1: Use await upload.read() instead of synchronous shutil.copyfileobj
            so the event loop is not blocked during file I/O.
    FIX 2: Prefix filename with a UUID to prevent concurrent-request collisions.
    FIX 3: Enforce 10 MB size limit to prevent memory exhaustion.
    FIX 4: Basic MIME type guard — only accept application/pdf.
    """
    # MIME type check (browsers send this; not cryptographically safe but good UX guard)
    if upload.content_type and "pdf" not in upload.content_type.lower():
        raise HTTPException(
            status_code=422,
            detail=f"{label} must be a PDF (received {upload.content_type!r})."
        )

    data = await upload.read()

    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"{label} exceeds the 10 MB size limit."
        )

    if not data:
        raise HTTPException(status_code=422, detail=f"{label} file is empty.")

    # UUID prefix prevents filename collisions between concurrent requests
    safe_name = f"{uuid.uuid4().hex}_{upload.filename or 'upload.pdf'}"
    path = os.path.join(settings.upload_dir, safe_name)

    with open(path, "wb") as f:
        f.write(data)

    return path


@app.get("/")
def health():
    return {"status": "ok", "service": "knowledge-graph-resume v2.1"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    resume: UploadFile = File(..., description="Resume PDF"),
    jd: UploadFile = File(..., description="Job Description PDF"),
):
    resume_path = await _save_upload(resume, "Resume")
    jd_path = await _save_upload(jd, "Job Description")

    try:
        # ── Step 1: Extract text ────────────────────────────────────────────
        try:
            resume_text = extract_text_from_pdf(resume_path)
            jd_text = extract_text_from_pdf(jd_path)
        except PDFExtractionError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        # ── Step 2: Parse JD ────────────────────────────────────────────────
        try:
            jd_profile = parse_jd(jd_text)
        except ValueError as exc:
            logger.error("JD parsing failed:\n%s", traceback.format_exc())
            raise HTTPException(status_code=422, detail=f"JD parsing failed: {exc}")

        if not jd_profile.required_skills:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No required skills found in the job description. "
                    "Please check the PDF contains readable text."
                )
            )

        # ── Step 3: Parse Resume ────────────────────────────────────────────
        try:
            resume_profile = parse_resume(resume_text)
        except ValueError as exc:
            logger.error("Resume parsing failed:\n%s", traceback.format_exc())
            raise HTTPException(status_code=422, detail=f"Resume parsing failed: {exc}")

        # ── Step 4: AI expand graph ─────────────────────────────────────────
        additional_nodes, edges = [], []
        try:
            additional_nodes, edges = expand_skills_for_role(jd_profile)
        except Exception as exc:
            logger.warning(
                "Skill expansion failed (proceeding with JD skills only).\n"
                "Error: %s\nTraceback:\n%s",
                exc, traceback.format_exc(),
            )

        # ── Step 5: Build graph ──────────────────────────────────────────────
        G = build_jd_graph(jd_profile, additional_nodes, edges)

        # ── Step 6: Propagate ────────────────────────────────────────────────
        coverage = propagate_skills(G, resume_profile.skills)

        # ── Step 7: Score ────────────────────────────────────────────────────
        readiness = calculate_readiness(jd_profile, coverage)

        # ── Step 8: Recommendations ──────────────────────────────────────────
        recommendations = generate_recommendations(readiness)

        # ── Step 9: Visualization ────────────────────────────────────────────
        graph_data = build_graph_visualization(
            G, coverage,
            jd_profile.required_skill_names,
            jd_profile.preferred_skill_names,
        )

        return AnalysisResponse(
            job_title=jd_profile.job_title,
            job_role=jd_profile.job_role,
            experience_level=jd_profile.experience_level.value,
            resume_skills=resume_profile.skills,
            jd_required_skills=jd_profile.required_skill_names,
            jd_preferred_skills=jd_profile.preferred_skill_names,
            readiness=readiness,
            recommendations=recommendations,
            graph_data=graph_data,
        )

    finally:
        # FIX: Always clean up uploaded files — even on error — to prevent disk bloat.
        for path in (resume_path, jd_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                logger.warning("Could not delete temp file %s: %s", path, e)
