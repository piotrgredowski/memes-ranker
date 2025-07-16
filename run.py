#!/usr/bin/env python3
"""Run the memes-ranker application."""

import uvicorn
from app.utils import get_app_config

if __name__ == "__main__":
    config = get_app_config()
    uvicorn.run(
        "app.main:app", host=config["host"], port=config["port"], reload=config["debug"]
    )
