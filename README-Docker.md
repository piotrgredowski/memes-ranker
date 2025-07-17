# Docker Setup with Tailwind CSS

This application now uses a multistage Docker build to compile Tailwind CSS for production use.

## How it works

1. **Stage 1 (css-builder)**: Uses Node.js to install Tailwind CSS dependencies and compile the CSS
1. **Stage 2 (production)**: Uses Python to run the FastAPI application with the compiled CSS

## Development Workflow

### Local Development

1. **Install Node.js dependencies**:

   ```bash
   npm install
   ```

1. **Build CSS locally**:

   ```bash
   npm run build:css:prod
   # or use the helper script
   ./dev-build-css.sh
   ```

1. **Run the application**:

   ```bash
   uv run python run.py
   ```

### Docker Development

1. **Build the Docker image**:

   ```bash
   docker build -t memes-ranker .
   ```

1. **Run with Docker Compose**:

   ```bash
   docker-compose up
   ```

## Production Deployment

The Docker image is now production-ready with:

- Compiled and minified Tailwind CSS
- No CDN dependencies
- Optimized for performance
- Multistage build for smaller image size

## Files Added/Modified

- `package.json` - Node.js dependencies and scripts
- `tailwind.config.js` - Tailwind configuration
- `Dockerfile` - Multistage build process
- `static/css/globals.css` - Updated with Tailwind directives
- `templates/base.html` - Updated to use compiled CSS
- `dev-build-css.sh` - Development helper script

## CSS Output

The compiled CSS is generated at `static/css/output.css` and includes:

- All Tailwind utilities
- Custom CSS variables for theme colors
- Existing component styles
- Minified for production

## Benefits

- ✅ No CDN dependency in production
- ✅ Smaller CSS file size (only used classes)
- ✅ Better performance
- ✅ Consistent styling across environments
- ✅ Easy to customize and extend
