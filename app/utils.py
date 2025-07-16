"""Utility functions for memes-ranker application."""

import os
import secrets
from io import BytesIO
from pathlib import Path
from typing import Optional

import qrcode
from coolname import generate_slug
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def generate_user_name() -> str:
    """Generate a fancy user name using coolname library.


    Returns:
        A fancy two-word user name like "brave-falcon"
    """
    return " ".join([word.capitalize() for word in generate_slug(2).split("-")])


def generate_session_token() -> str:
    """Generate a secure session token.

    Returns:
        A secure random token for user sessions
    """
    return secrets.token_urlsafe(32)


def generate_qr_code(url: Optional[str] = None) -> bytes:
    """Generate QR code image as bytes.

    Args:
        url: URL to encode in QR code. If None, uses QR_CODE_URL from env

    Returns:
        QR code image as bytes (PNG format)
    """
    if url is None:
        url = os.getenv("QR_CODE_URL", "https://memes.bieda.it")

    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes.getvalue()


def get_memes_directory() -> Path:
    """Get the memes directory path.

    Returns:
        Path to memes directory
    """
    memes_dir = os.getenv("MEMES_DIR", "./static/memes")
    return Path(memes_dir)


def get_meme_files() -> list[str]:
    """Get list of meme files in the memes directory.

    Returns:
        List of meme filenames
    """
    memes_dir = get_memes_directory()
    if not memes_dir.exists():
        return []

    # Supported image formats
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    meme_files = []
    for file_path in memes_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            meme_files.append(file_path.name)

    return sorted(meme_files)


def get_database_path() -> str:
    """Get database path from environment.

    Returns:
        Database file path
    """
    return os.getenv("DATABASE_PATH", "./data/memes.db")


def get_admin_password() -> str:
    """Get admin password from environment.

    Returns:
        Admin password
    """
    return os.getenv("ADMIN_PASSWORD", "admin123")


def get_jwt_secret() -> str:
    """Get JWT secret key from environment.

    Returns:
        JWT secret key
    """
    return os.getenv("JWT_SECRET_KEY", "fallback_secret_key_change_in_production")


def get_app_config() -> dict:
    """Get application configuration from environment.

    Returns:
        Application configuration dictionary
    """
    return {
        "host": os.getenv("APP_HOST", "0.0.0.0"),
        "port": int(os.getenv("APP_PORT", "8000")),
        "debug": os.getenv("APP_DEBUG", "true").lower() == "true",
    }
