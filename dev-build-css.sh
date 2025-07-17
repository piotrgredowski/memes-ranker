#!/bin/bash

# Development script to build CSS with Tailwind
# This script builds CSS for local development

echo "Building CSS with Tailwind..."
npm run build:css:prod

echo "CSS built successfully!"
echo "The built CSS is available at: static/css/output.css"
echo ""
echo "To run the app locally with the new CSS:"
echo "  uv run python run.py"
