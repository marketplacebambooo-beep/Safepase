from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.voice import lookup_prompt, render_say_xml

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/callback")
async def voice_callback(request: Request, db: Session = Depends(get_db)):
    """Africa's Talking Voice XML callback — speak the stored emergency brief."""
    form = await request.form()
    is_active = str(form.get("isActive", "1"))
    if is_active != "1":
        return PlainTextResponse("ok")

    session_id = str(form.get("sessionId") or "")
    request_id = str(form.get("clientRequestId") or form.get("clientRequestID") or "")
    recipient = str(form.get("destinationNumber") or form.get("callerNumber") or "")
    prompt = lookup_prompt(db, session_id=session_id, request_id=request_id, recipient=recipient)
    return PlainTextResponse(content=render_say_xml(prompt.message if prompt else ""), media_type="text/plain")
