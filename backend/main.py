"""C-SSRS Electronic Assessment System — FastAPI Backend"""
import socket
import uuid

def get_local_ip():
    """Get LAN IP for QR code URL"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
LOCAL_PORT = 8000
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

import qrcode
import io

from scorer import (
    IdeationAnswers, IntensityAnswers, BehaviorAnswers, score_assessment,
)
from models import SessionCreate, AssessRequest, AssessmentResponse
from database import (
    init_db, save_assessment, get_assessment, list_assessments, get_patient_history,
    create_session, get_session, resolve_access_code, search_by_phone,
)

app = FastAPI(title="C-SSRS Electronic Assessment System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files — serve ../frontend/ at /static/
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.on_event("startup")
def startup():
    init_db()


# Also init on import (for testing and direct script usage)
init_db()


# ── Page routes ──

@app.get("/")
def serve_doctor_page():
    doctor_html = frontend_dir / "doctor.html"
    if doctor_html.exists():
        return FileResponse(str(doctor_html), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "C-SSRS Electronic Assessment System API", "docs": "/docs"}


@app.get("/patient.html")
def serve_patient_page():
    patient_html = frontend_dir / "patient.html"
    if patient_html.exists():
        return FileResponse(str(patient_html))
    raise HTTPException(status_code=404, detail="patient.html not found")


@app.get("/code")
def serve_code_page():
    code_html = frontend_dir / "code.html"
    if code_html.exists():
        return FileResponse(str(code_html))
    raise HTTPException(status_code=404, detail="code.html not found")




@app.get("/code.html")
def serve_code_html():
    from fastapi import Response
    c = frontend_dir / "code.html"
    if not c.exists():
        raise HTTPException(404)
    with open(c, "r") as f:
        content = f.read()
    return Response(content=content, media_type="text/html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# ── API routes ──

@app.get("/api/code/{code}")
def lookup_code(code: str):
    """Resolve a short access code to a session"""
    session = resolve_access_code(code)
    if session is None:
        raise HTTPException(status_code=404, detail="Access code not found")
    return {
        "session_id": session["session_id"],
        "patient_id": session["patient_id"],
        "patient_phone": session.get("patient_phone"),
        "access_code": session["access_code"],
    }

@app.post("/api/sessions")
def create_session_endpoint(req: SessionCreate):
    session_id = req.session_id or str(uuid.uuid4())
    access_code = create_session(session_id, req.patient_id, req.version, req.patient_phone)
    return {
        "session_id": session_id,
        "patient_id": req.patient_id,
        "patient_phone": req.patient_phone,
        "access_code": access_code,
        "version": req.version,
        "created_at": datetime.utcnow().isoformat(),
    }


@app.get("/api/sessions/{session_id}")
def get_session_status(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assessment = get_assessment(session_id)
    return {
        "session_id": session["session_id"],
        "patient_id": session["patient_id"],
        "version": session["version"],
        "created_at": session["created_at"],
        "assessed": assessment is not None,
        "risk_level": assessment.get("risk_level") if assessment else None,
    }


@app.post("/api/assess/{session_id}", response_model=AssessmentResponse)
def submit_assessment(session_id: str, req: AssessRequest):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    patient_id = session["patient_id"]
    patient_phone = session.get("patient_phone")
    version = session["version"]

    ideation = IdeationAnswers(**req.ideation.model_dump())
    intensity = IntensityAnswers(**req.intensity.model_dump())
    behavior = BehaviorAnswers(**req.behavior.model_dump())

    result = score_assessment(
        session_id=session_id,
        patient_id=patient_id,
        ideation=ideation,
        intensity=intensity,
        behavior=behavior,
        lethality=req.lethality,
    )

    result_dict = result.to_dict()
    result_dict["version"] = version
    # Use phone from request if provided, else from session
    result_dict["patient_phone"] = req.patient_phone or patient_phone
    # Flatten nested structures for DB columns
    result_dict["severity_score"] = result.ideation_severity_score
    result_dict["severity_name"] = result.ideation_severity_name
    result_dict["intensity_total"] = result.intensity_total
    result_dict["intensity_level"] = result.intensity_level

    # Add raw input fields — map intensity field names to DB column names
    ideation_raw = req.ideation.model_dump()
    result_dict.update(ideation_raw)

    intensity_raw = req.intensity.model_dump()
    result_dict["intensity_frequency"] = intensity_raw.get("frequency")
    result_dict["intensity_duration"] = intensity_raw.get("duration")
    result_dict["intensity_controllability"] = intensity_raw.get("controllability")
    result_dict["intensity_deterrents"] = intensity_raw.get("deterrents")
    result_dict["intensity_reason"] = intensity_raw.get("reason")

    behavior_raw = req.behavior.model_dump()
    result_dict.update(behavior_raw)
    result_dict["lethality_level"] = req.lethality

    save_assessment(result_dict)

    return AssessmentResponse(**result_dict)


@app.get("/api/report")
def list_reports():
    rows = list_assessments()
    return rows


@app.get("/api/report/{session_id}")
def get_report(session_id: str):
    row = get_assessment(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return row


@app.get("/api/patient/{patient_id}/history")
def patient_history(patient_id: str):
    rows = get_patient_history(patient_id)
    return {"patient_id": patient_id, "assessments": rows}


@app.get("/api/search")
def search_patient(phone: str):
    """Search assessments by patient phone number (partial match)."""
    if not phone or len(phone.strip()) < 4:
        raise HTTPException(400, "请输入至少4位手机号")
    rows = search_by_phone(phone.strip())
    return {"phone": phone, "count": len(rows), "assessments": rows}


@app.get("/api/export/scores")
def export_scores():
    """Export all assessment scores for research analysis (CSV format)"""
    rows = list_assessments()
    import csv
    import io

    output = io.StringIO()
    if not rows:
        return {"error": "No assessments found"}

    fields = [
        "patient_id", "assessment_date",
        "severity_score", "severity_name",
        "intensity_frequency", "intensity_duration", "intensity_controllability",
        "intensity_deterrents", "intensity_reason", "intensity_total", "intensity_level",
        "risk_level", "risk_label",
        "lethality_level",
        "b1_actual_attempt", "b2_interrupted", "b3_aborted", "b4_preparatory", "b5_nssi",
        "immediate_actions", "follow_up",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8")


@app.get("/api/summary")
def summary_endpoint(limit: int = 5):
    """脱敏摘要 — 仅返回访问码、风险等级，不包含答卷细节"""
    rows = list_assessments()
    return {
        "total": len(rows),
        "latest": [
            {
                "access_code": r.get("session_id", "")[:6],
                "patient_id": r.get("patient_id", ""),
                "risk_level": r.get("risk_level", ""),
                "risk_label": r.get("risk_label", ""),
                "assessment_date": r.get("assessment_date", ""),
            }
            for r in rows[:limit]
        ],
    }


@app.get("/mobile")
def serve_mobile_doctor():
    mobile_html = frontend_dir / "mobile-doctor.html"
    if mobile_html.exists():
        return FileResponse(str(mobile_html), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    raise HTTPException(status_code=404, detail="mobile-doctor.html not found")


@app.get("/doctor-qr")
def serve_doctor_qr_page():
    qr_html = frontend_dir / "doctor-qr-page.html"
    if qr_html.exists():
        return FileResponse(str(qr_html), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    raise HTTPException(status_code=404, detail="doctor-qr-page.html not found")


@app.get("/doctor-qr.png")
def serve_doctor_qr_image():
    qr_png = frontend_dir / "doctor-qr-mobile.png"
    if qr_png.exists():
        return FileResponse(str(qr_png), headers={"Cache-Control": "public, max-age=31536000"})
    raise HTTPException(status_code=404, detail="doctor-qr-mobile.png not found")


@app.get("/api/qr-link/{session_id}")
def generate_patient_link(session_id: str):
    """Generate a direct patient URL for a session (for QR code)"""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Return the access code so frontend can build QR URL
    access_code = session.get("access_code", "")
    phone = session.get("patient_phone", "")
    patient_url = f"http://82.156.238.242:8888/patient.html?session={session_id}"
    if phone:
        patient_url += f"&phone={phone}"
    return {
        "patient_url": patient_url,
        "access_code": access_code,
        "session_id": session_id,
    }


@app.get("/api/qr/{access_code}")
def generate_qr(access_code: str):
    """Generate a QR code PNG that links to the patient self-assessment page via cloud gateway."""
    qr_url = f"http://82.156.238.242:8888/code?code={access_code}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")
