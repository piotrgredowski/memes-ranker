"""Main FastAPI application for memes-ranker."""

import os
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    Depends,
    Form,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .auth import authenticate_admin, create_admin_token, get_current_admin
from .database import db
from .websocket_manager import websocket_manager
from .events import event_broadcaster
from .logging_config import (
    setup_logging,
    get_logger,
    setup_fastapi_error_logging,
    setup_frontend_logging,
    get_frontend_loggers,
)
from .models import FrontendLogBatch, SessionRequest, RankingRequest
from .utils import (
    generate_user_name,
    generate_session_token,
    generate_qr_code,
    get_meme_files,
    get_app_config,
)

# Configure logging
setup_logging()
setup_frontend_logging()

# Create FastAPI app
app = FastAPI(
    title="Memes Ranker",
    description="A FastAPI application for ranking memes",
    version="1.0.0",
)

# Setup error logging middleware
setup_fastapi_error_logging(app)

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

# Initialize WebSocket event broadcaster
event_broadcaster.set_websocket_manager(websocket_manager)


# WebSocket endpoints
@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    """WebSocket endpoint for admin real-time updates."""
    client_id = f"admin_{id(websocket)}"
    await websocket_manager.connect(websocket, "admin", client_id)

    try:
        while True:
            # Listen for incoming messages (mainly for ping/pong)
            data = await websocket.receive_text()
            # For now, just echo back (can be enhanced for bidirectional communication)
            await websocket_manager.send_personal_message(
                websocket, {"type": "echo", "data": data}
            )
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)


@app.websocket("/ws/user")
async def websocket_user_endpoint(websocket: WebSocket):
    """WebSocket endpoint for user real-time updates."""
    client_id = f"user_{id(websocket)}"
    await websocket_manager.connect(websocket, "users", client_id)

    try:
        while True:
            # Listen for incoming messages
            data = await websocket.receive_text()
            # Echo back for now
            await websocket_manager.send_personal_message(
                websocket, {"type": "echo", "data": data}
            )
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)


# Pydantic models
class LoginRequest(BaseModel):
    password: str


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

    # Check if there's an active session
    active_session = await db.get_active_session()

    # If no active session, show waiting screen
    if not active_session:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user_name": user["name"],
                "session_token": session_token,
                "memes": [],
                "current_meme": None,
                "user_rankings": [],
                "active_session": None,
                "qr_code_url": os.getenv("QR_CODE_URL", "https://memes.bieda.it"),
            },
        )

    # Get active memes
    memes = await db.get_active_memes()

    # Get user's rankings from current session only
    user_rankings = await db.get_user_rankings_for_session(
        user["id"], active_session["id"]
    )
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
            "session_token": session_token,
            "memes": memes,
            "current_meme": current_meme,
            "user_rankings": user_rankings,
            "active_session": active_session,
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

    # Check if there's an active session
    active_session = await db.get_active_session()
    if not active_session:
        raise HTTPException(
            status_code=403,
            detail="No active session. Please wait for an admin to start a session.",
        )

    # Validate score
    if not (0 <= ranking.score <= 10):
        raise HTTPException(status_code=400, detail="Score must be between 0 and 10")

    # Create/update ranking
    await db.create_ranking(user["id"], ranking.meme_id, ranking.score)

    # Broadcast updated stats to admin dashboard
    await websocket_manager.broadcast_connection_stats()

    return {"status": "success", "message": "Ranking submitted"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/admin/login")
async def admin_login_post(password: str = Form(...)):
    """Admin login endpoint."""
    logger = get_logger(__name__)
    logger.info("Admin login attempt", password_length=len(password))

    if not authenticate_admin(password):
        logger.warning("Admin authentication failed")
        raise HTTPException(status_code=401, detail="Invalid password")

    logger.info("Admin authentication successful, creating token")
    token = create_admin_token()
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(
        key="admin_token",
        value=token,
        max_age=12 * 60 * 60,  # 12 hours
        httponly=True,
        secure=False,  # Set to True in production
    )
    logger.info("Redirecting to admin dashboard")
    return response


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: dict = Depends(get_current_admin)):
    """Admin dashboard."""
    logger = get_logger(__name__)
    logger.info("Admin dashboard accessed", admin_user=admin["username"])
    # Get statistics
    meme_stats = await db.get_meme_stats()
    active_session = await db.get_active_session()

    # Get session statistics if there's an active session
    session_stats = None
    if active_session:
        session_stats = await db.get_session_stats(active_session["id"])

    # Get completed sessions for results publishing
    completed_sessions = await db.get_completed_sessions_with_results()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "is_dashboard": True,
            "user_name": admin["username"],
            "session_token": request.cookies.get("session_token"),
            "meme_stats": meme_stats,
            "active_session": active_session,
            "session_stats": session_stats,
            "completed_sessions": completed_sessions,
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


@app.post("/admin/session/finish")
async def finish_session(admin: dict = Depends(get_current_admin)):
    """Finish the current active session."""
    active_session = await db.get_active_session()

    if not active_session:
        raise HTTPException(status_code=404, detail="No active session found")

    await db.end_session(active_session["id"])
    return {"status": "success", "message": "Session finished successfully"}


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

    # Broadcast memes populated event
    try:
        await event_broadcaster.broadcast_memes_populated(len(meme_files))
    except Exception as e:
        logger = get_logger(__name__)
        logger.error("Failed to broadcast memes populated event", error=str(e))

    return {"status": "success", "memes_added": len(meme_files)}


# Results reveal endpoints
@app.post("/admin/results/start/{session_id}")
async def start_results_reveal(
    session_id: int, admin: dict = Depends(get_current_admin)
):
    """Start results reveal for a session."""
    try:
        # Check if session exists and is finished
        async with db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await cursor.fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        session_dict = dict(session)
        if session_dict.get("active", False):
            raise HTTPException(
                status_code=400, detail="Cannot reveal results for active session"
            )

        # Initialize results reveal
        await db.create_results_reveal(session_id)

        return {"status": "success", "message": "Results reveal started"}
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error starting results reveal: {e}")
        raise HTTPException(status_code=500, detail="Failed to start results reveal")


@app.get("/admin/results/{session_id}")
async def admin_results_page(
    session_id: int, request: Request, admin: dict = Depends(get_current_admin)
):
    """Admin results reveal interface."""
    try:
        # Get session and results
        async with db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await cursor.fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        results = await db.get_session_results(session_id)
        reveal_status = await db.get_reveal_status(session_id)

        # If no reveal status exists, initialize it
        if not reveal_status:
            await db.create_results_reveal(session_id)
            reveal_status = await db.get_reveal_status(session_id)

        return templates.TemplateResponse(
            "admin_results.html",
            {
                "request": request,
                "session": dict(session),
                "results": results,
                "reveal_status": reveal_status,
                "total_positions": len(results),
            },
        )
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error loading admin results page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load results page")


@app.post("/admin/results/{session_id}/next")
async def reveal_next_position(
    session_id: int, admin: dict = Depends(get_current_admin)
):
    """Reveal next position in results."""
    try:
        results = await db.get_session_results(session_id)
        reveal_status = await db.get_reveal_status(session_id)

        current_position = reveal_status.get("current_position", 0)
        max_position = len(results)

        if current_position >= max_position:
            raise HTTPException(
                status_code=400, detail="All positions already revealed"
            )

        new_position = current_position + 1
        await db.update_reveal_position(session_id, new_position)

        # Mark as complete if we've revealed all positions
        if new_position >= max_position:
            await db.complete_reveal(session_id)

        # Get the meme for this position
        meme_data = None
        for result in results:
            if result["position"] == new_position:
                meme_data = await db.get_meme_detailed_stats(result["id"], session_id)
                break

        # Broadcast to WebSocket clients
        try:
            await websocket_manager.broadcast_reveal_update(
                session_id, new_position, meme_data
            )
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error broadcasting reveal update: {e}")

        return {
            "position": new_position,
            "is_complete": new_position >= max_position,
            "meme_data": meme_data,
        }
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error revealing next position: {e}")
        raise HTTPException(status_code=500, detail="Failed to reveal next position")


@app.post("/admin/results/{session_id}/previous")
async def reveal_previous_position(
    session_id: int, admin: dict = Depends(get_current_admin)
):
    """Go back to previous position."""
    try:
        reveal_status = await db.get_reveal_status(session_id)
        current_position = reveal_status.get("current_position", 0)

        if current_position <= 0:
            raise HTTPException(status_code=400, detail="Already at first position")

        new_position = current_position - 1
        await db.update_reveal_position(session_id, new_position)

        return {"position": new_position}
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error going to previous position: {e}")
        raise HTTPException(status_code=500, detail="Failed to go to previous position")


@app.post("/admin/results/{session_id}/reset")
async def reset_results_reveal(
    session_id: int, admin: dict = Depends(get_current_admin)
):
    """Reset results reveal to beginning."""
    try:
        await db.update_reveal_position(session_id, 0)
        return {"status": "success", "message": "Results reveal reset"}
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error resetting results reveal: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset results reveal")


# Public results endpoints
@app.get("/results/{session_id}")
async def public_results_view(session_id: int, request: Request):
    """Public/User view of revealed results - accessible to all users."""
    try:
        # Get session and results
        async with db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await cursor.fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        results = await db.get_session_results(session_id)
        reveal_status = await db.get_reveal_status(session_id)

        # Get user's rankings for this session if they have a session token
        user_rankings = []
        session_token = request.cookies.get("session_token")
        if session_token:
            try:
                user = await db.get_user_by_token(session_token)
                if user:
                    user_rankings = await db.get_user_rankings_for_session(
                        user["id"], session_id
                    )
            except Exception:
                pass  # Ignore errors getting user rankings

        return templates.TemplateResponse(
            "public_results.html",
            {
                "request": request,
                "session": dict(session),
                "results": results,
                "reveal_status": reveal_status,
                "user_rankings": user_rankings,
                "total_positions": len(results),
            },
        )
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error loading public results page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load results page")


@app.get("/past-results")
async def past_results_page(request: Request):
    """Past results archive page - list all completed sessions."""
    try:
        completed_sessions = await db.get_completed_sessions_with_results()

        return templates.TemplateResponse(
            "past_results.html",
            {
                "request": request,
                "sessions": completed_sessions,
            },
        )
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error loading past results page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load past results page")


@app.get("/api/past-results")
async def get_past_results_api():
    """API endpoint for past results data."""
    try:
        completed_sessions = await db.get_completed_sessions_with_results()
        return {"sessions": completed_sessions}
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error getting past results: {e}")
        raise HTTPException(status_code=500, detail="Failed to get past results")


@app.get("/api/results/{session_id}/status")
async def get_reveal_status_api(session_id: int):
    """Get current reveal status (for WebSocket updates)."""
    try:
        reveal_status = await db.get_reveal_status(session_id)
        results = await db.get_session_results(session_id)

        return {
            "session_id": session_id,
            "current_position": reveal_status.get("current_position", 0),
            "is_complete": reveal_status.get("is_complete", False),
            "total_positions": len(results),
        }
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error getting reveal status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get reveal status")


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


@app.get("/api/session/stats")
async def get_session_stats(admin: dict = Depends(get_current_admin)):
    """API endpoint to get session statistics with real-time data."""
    active_session = await db.get_active_session()

    if not active_session:
        return {"error": "No active session"}

    # Get session stats from database
    session_stats = await db.get_session_stats(active_session["id"])

    # Get real-time connection stats from WebSocket manager
    connection_stats = websocket_manager.get_connection_stats()

    # Calculate expected votes (unique participating users × memes)
    # Use the higher of currently connected users or users who have already participated
    effective_users = max(
        connection_stats["user_connections"], session_stats.get("unique_users_count", 0)
    )
    expected_votes = effective_users * session_stats.get("meme_count", 0)

    return {
        "session": session_stats.get("session", {}),
        "connected_users": connection_stats["user_connections"],
        "total_votes": session_stats.get("vote_count", 0),
        "meme_count": session_stats.get("meme_count", 0),
        "expected_votes": expected_votes,
        "connection_stats": connection_stats,
    }


@app.get("/api/session/status")
async def get_session_status():
    """Public API endpoint to check if there's an active session."""
    active_session = await db.get_active_session()
    return {
        "has_active_session": active_session is not None,
        "session_name": active_session["name"] if active_session else None,
    }


@app.post("/api/frontend-logs")
async def receive_frontend_logs(request: Request, log_batch: FrontendLogBatch):
    """Receive and process frontend logs."""
    import json
    from datetime import datetime

    # Get loggers
    json_logger, text_logger = get_frontend_loggers()

    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Process each log entry
    for log_entry in log_batch.logs:
        # Prepare log data
        log_data = {
            "timestamp": log_entry.timestamp.isoformat(),
            "level": log_entry.level,
            "message": log_entry.message,
            "url": log_entry.url,
            "user_agent": log_entry.user_agent or user_agent,
            "session_id": log_entry.session_id,
            "user_id": log_entry.user_id,
            "component": log_entry.component,
            "action": log_entry.action,
            "metadata": log_entry.metadata,
            "stack_trace": log_entry.stack_trace,
            "client_ip": client_ip,
            "server_timestamp": datetime.now().isoformat(),
        }

        # Add client info from batch
        if log_batch.client_info:
            log_data["client_info"] = log_batch.client_info

        # Log to JSON file
        json_logger.info(json.dumps(log_data))

        # Log to text file
        text_message = f"[{log_entry.level.upper()}] {log_entry.message}"
        if log_entry.component:
            text_message += f" | Component: {log_entry.component}"
        if log_entry.action:
            text_message += f" | Action: {log_entry.action}"
        if log_entry.session_id:
            text_message += f" | Session: {log_entry.session_id}"
        if log_entry.user_id:
            text_message += f" | User: {log_entry.user_id}"
        text_message += f" | URL: {log_entry.url}"
        if log_entry.metadata:
            text_message += f" | Metadata: {json.dumps(log_entry.metadata)}"

        # Log to appropriate level
        if log_entry.level == "debug":
            text_logger.debug(text_message)
        elif log_entry.level == "info":
            text_logger.info(text_message)
        elif log_entry.level == "warn":
            text_logger.warning(text_message)
        elif log_entry.level == "error":
            text_logger.error(text_message)
            if log_entry.stack_trace:
                text_logger.error(f"Stack trace: {log_entry.stack_trace}")

    return {"status": "success", "processed": len(log_batch.logs)}


# Initialize memes on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Populate memes if directory exists and has files
    meme_files = get_meme_files()
    if meme_files:
        existing_memes = await db.get_active_memes()
        if not existing_memes:
            logger = get_logger(__name__)
            logger.info("Populating memes from directory", meme_count=len(meme_files))
            for filename in meme_files:
                path = f"/static/memes/{filename}"
                await db.create_meme(filename, path)


if __name__ == "__main__":
    import uvicorn

    config = get_app_config()
    uvicorn.run(app, host=config["host"], port=config["port"], reload=config["debug"])
