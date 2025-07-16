"""Main FastAPI application for memes-ranker."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .auth import authenticate_admin, create_admin_token, get_current_admin
from .database import db
from .utils import (
    generate_user_name,
    generate_session_token,
    generate_qr_code,
    get_meme_files,
    get_app_config,
)

# Create FastAPI app
app = FastAPI(
    title="Memes Ranker",
    description="A FastAPI application for ranking memes",
    version="1.0.0",
)

# Create directories
Path("static").mkdir(exist_ok=True)
Path("static/css").mkdir(exist_ok=True)
Path("static/js").mkdir(exist_ok=True)
Path("static/memes").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")


# Pydantic models
class LoginRequest(BaseModel):
    password: str


class RankingRequest(BaseModel):
    meme_id: int
    score: int


class SessionRequest(BaseModel):
    name: str


# Helper functions
def get_user_session(request: Request) -> Optional[dict]:
    """Get user session from cookies."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None

    # This would be async in real implementation
    return {"session_token": session_token}


# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main ranking page."""
    # Get or create user session
    session_token = request.cookies.get("session_token")
    if not session_token:
        # Create new user
        user_name = generate_user_name()
        session_token = generate_session_token()

        await db.create_user(user_name, session_token)

        # Create response with cookie
        response = templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user_name": user_name,
                "memes": [],
                "current_meme": None,
                "qr_code_url": os.getenv("QR_CODE_URL", "https://memes.bieda.it"),
            },
        )
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
        )
        return response

    # Get existing user
    user = await db.get_user_by_token(session_token)
    if not user:
        # Invalid token, redirect to clear cookie
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie("session_token")
        return response

    # Get active memes
    memes = await db.get_active_memes()

    # Get user's rankings to find next unranked meme
    user_rankings = await db.get_user_rankings(user["id"])
    ranked_meme_ids = {r["meme_id"] for r in user_rankings}

    # Find next meme to rank
    current_meme = None
    for meme in memes:
        if meme["id"] not in ranked_meme_ids:
            current_meme = meme
            break

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user_name": user["name"],
            "memes": memes,
            "current_meme": current_meme,
            "user_rankings": user_rankings,
            "qr_code_url": os.getenv("QR_CODE_URL", "https://memes.bieda.it"),
        },
    )


@app.post("/rank")
async def rank_meme(request: Request, ranking: RankingRequest):
    """Submit a meme ranking."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="No session token")

    user = await db.get_user_by_token(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token")

    # Validate score
    if not (0 <= ranking.score <= 10):
        raise HTTPException(status_code=400, detail="Score must be between 0 and 10")

    # Create/update ranking
    await db.create_ranking(user["id"], ranking.meme_id, ranking.score)

    return {"status": "success", "message": "Ranking submitted"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/admin/login")
async def admin_login_post(password: str = Form(...)):
    """Admin login endpoint."""
    print(f"Admin login attempt with password: {password}")

    if not authenticate_admin(password):
        print("Authentication failed")
        raise HTTPException(status_code=401, detail="Invalid password")

    print("Authentication successful, creating token")
    token = create_admin_token()
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(
        key="admin_token",
        value=token,
        max_age=12 * 60 * 60,  # 12 hours
        httponly=True,
        secure=False,  # Set to True in production
    )
    print("Redirecting to dashboard")
    return response


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: dict = Depends(get_current_admin)):
    """Admin dashboard."""
    print(f"Admin dashboard accessed by: {admin}")
    # Get statistics
    meme_stats = await db.get_meme_stats()
    active_session = await db.get_active_session()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "is_dashboard": True,
            "meme_stats": meme_stats,
            "active_session": active_session,
            "qr_code_url": os.getenv("QR_CODE_URL", "https://memes.bieda.it"),
        },
    )


@app.post("/admin/session")
async def create_session(
    session: SessionRequest, admin: dict = Depends(get_current_admin)
):
    """Create a new session."""
    session_id = await db.create_session(session.name)
    await db.start_session(session_id)
    return {"status": "success", "session_id": session_id}


@app.post("/admin/memes/populate")
async def populate_memes(admin: dict = Depends(get_current_admin)):
    """Populate memes from files in static/memes directory."""
    meme_files = get_meme_files()

    if not meme_files:
        raise HTTPException(
            status_code=400, detail="No meme files found in static/memes"
        )

    # Clear existing memes
    existing_memes = await db.get_active_memes()
    for meme in existing_memes:
        await db.set_meme_active(meme["id"], False)

    # Add new memes
    for filename in meme_files:
        path = f"/static/memes/{filename}"
        await db.create_meme(filename, path)

    return {"status": "success", "memes_added": len(meme_files)}


@app.get("/qr-code")
async def get_qr_code():
    """Generate QR code image."""
    qr_bytes = generate_qr_code()
    return Response(content=qr_bytes, media_type="image/png")


@app.get("/api/memes")
async def get_memes():
    """API endpoint to get all active memes."""
    memes = await db.get_active_memes()
    return {"memes": memes}


@app.get("/api/stats")
async def get_stats():
    """API endpoint to get meme statistics."""
    stats = await db.get_meme_stats()
    return {"stats": stats}


# Initialize memes on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Populate memes if directory exists and has files
    meme_files = get_meme_files()
    if meme_files:
        existing_memes = await db.get_active_memes()
        if not existing_memes:
            print(f"Populating {len(meme_files)} memes from static/memes directory")
            for filename in meme_files:
                path = f"/static/memes/{filename}"
                await db.create_meme(filename, path)


if __name__ == "__main__":
    import uvicorn

    config = get_app_config()
    uvicorn.run(app, host=config["host"], port=config["port"], reload=config["debug"])
