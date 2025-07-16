#!/usr/bin/env python3
"""Run the memes-ranker application."""

import sys

import uvicorn

from app.utils import get_app_config

if __name__ == "__main__":
    config = get_app_config()

    # Enable reload by default for development, or if --reload is passed
    reload = config["debug"] or "--reload" in sys.argv

    uvicorn.run("app.main:app", host=config["host"], port=config["port"], reload=reload)
