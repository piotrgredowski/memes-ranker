# Memes Ranker Application Plan

## Overview

FastAPI-based meme ranking application with shadcn/ui frontend components, SQLite database with plain SQL, and Docker deployment supporting up to 2000 concurrent users.

## Project Structure

```
memes-ranker/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLite connection and queries
│   ├── auth.py              # Admin authentication
│   └── utils.py             # Utility functions
├── static/
│   ├── css/
│   │   ├── globals.css      # Global styles with CSS variables
│   │   └── components.css   # shadcn/ui component styles
│   ├── js/
│   │   ├── app.js           # Main application JavaScript
│   │   └── components.js    # Simple component interactions
│   └── memes/               # Meme images directory
├── templates/
│   ├── index.html           # Main ranking page
│   ├── admin.html           # Admin dashboard
│   └── base.html            # Base template
├── sql/
│   └── schema.sql           # Database schema
├── plans/
│   └── initial_plan.md      # This plan document
├── .env                     # Environment variables (secrets)
├── .env.example             # Example environment file
├── .gitignore               # Git ignore file
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

## Core Features

### 1. User Experience (shadcn/ui Components)

- **Unique Names**: Use `coolname` library for fancy two-word user names
- **Ranking Interface**: shadcn/ui Slider component (0-10) for rating memes
- **Navigation**: shadcn/ui Button components for forward/back with proper state management
- **QR Code**: Display QR code pointing to https://memes.bieda.it using shadcn/ui Card component
- **User Name Display**: Show assigned name persistently in shadcn/ui Badge component
- **Accessibility**: Full keyboard navigation, ARIA labels, and screen reader support

### 2. Admin Features (shadcn/ui Components)

- **Authentication**: Simple password-based admin login using shadcn/ui Form components
- **Session Management**: Start new rounds, set time limits using shadcn/ui Dialog and Input components
- **Statistics**: View meme thumbnails and ranking counts in shadcn/ui Table and Card components
- **QR Code**: Admin page displays the QR code using shadcn/ui Card component

### 3. Database Schema (SQLite with Plain SQL)

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memes table
CREATE TABLE memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rankings table
CREATE TABLE rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meme_id INTEGER NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (meme_id) REFERENCES memes(id),
    UNIQUE(user_id, meme_id)
);

-- Sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Technical Implementation

- **FastAPI**: Main web framework with Jinja2 templates
- **sqlite3**: Built-in Python SQLite driver with plain SQL
- **aiosqlite**: Async SQLite operations for better concurrency
- **uvicorn**: ASGI server
- **qrcode**: QR code generation
- **coolname**: Fancy name generation
- **shadcn/ui**: CSS-only component library for consistent, accessible UI
- **Static files**: CSS/JS served by FastAPI

### 5. Database Layer

- **Connection pooling**: Use aiosqlite for async operations
- **WAL mode**: Enable Write-Ahead Logging for better concurrency
- **Prepared statements**: Prevent SQL injection
- **Transaction management**: Ensure data consistency

### 6. Environment Variables (.env)

- **ADMIN_PASSWORD**: Admin dashboard password
- **JWT_SECRET_KEY**: Secret key for JWT token generation
- **DATABASE_PATH**: Path to SQLite database file
- **MEMES_DIR**: Directory containing meme images
- **QR_CODE_URL**: URL for QR code generation (https://memes.bieda.it)

### 7. Docker Configuration

- **Multi-stage build**: Optimize image size
- **Volume mounts**: For memes and database persistence
- **Environment variables**: Load from .env file
- **Health checks**: Ensure container reliability

### 8. Performance Considerations

- **SQLite WAL mode**: Support concurrent reads/writes
- **Connection management**: Proper async connection handling
- **Static file caching**: Efficient asset serving
- **Session management**: JWT tokens for user sessions

## Implementation Steps

1. Set up project structure and dependencies
1. Create database schema and connection management ✅
1. Set up shadcn/ui CSS framework and components
1. Implement FastAPI routes with plain SQL queries
1. Build HTML templates with shadcn/ui components
1. Add minimal JavaScript for component interactions
1. Create admin dashboard with authentication
1. Implement QR code generation
1. Add Docker configuration
1. Test with load simulation and accessibility
1. Deploy and monitor

## Database Setup

### Files Created

- `sql/schema.sql` - Database schema with tables for users, memes, rankings, and sessions
- `setup_db.py` - Database initialization script
- `app/database.py` - Async SQLite database operations using aiosqlite

### Database Setup Commands

```bash
# Initialize database (run once)
python setup_db.py

# The database will be created at: data/memes.db
# Schema includes proper indexes for performance
# WAL mode enabled for better concurrency
```

### Database Features

- **Async Operations**: Uses aiosqlite for non-blocking database operations
- **Connection Management**: Proper connection handling with context managers
- **WAL Mode**: Write-Ahead Logging for better concurrency (supports up to 2000 users)
- **Foreign Key Constraints**: Ensures data integrity
- **Proper Indexing**: Optimized for common queries
- **UPSERT Support**: Rankings can be updated if user re-rates a meme

## shadcn/ui Components Used

- **Button**: Navigation controls, form submissions
- **Card**: Meme display, QR code container, statistics
- **Badge**: User name display, status indicators
- **Slider**: Meme rating input (0-10)
- **Form**: Admin login, session management
- **Input**: Text inputs for admin forms
- **Dialog**: Modal dialogs for admin actions
- **Table**: Statistics and rankings display
- **Progress**: Loading states and session timers

## Dependencies

- fastapi
- uvicorn[standard]
- aiosqlite
- jinja2
- python-multipart
- qrcode[pil]
- coolname
- passlib[bcrypt]
- python-jose[cryptography]
- python-dotenv

## Environment Configuration

All sensitive configuration should be stored in `.env` file:

```bash
# .env file example
ADMIN_PASSWORD=your_secure_admin_password
JWT_SECRET_KEY=your_jwt_secret_key_here
DATABASE_PATH=./data/memes.db
MEMES_DIR=./static/memes
QR_CODE_URL=https://memes.bieda.it
```

The `.env` file must be excluded from version control by adding it to `.gitignore`.

## UI Design Principles

- **Simplicity**: Clean, minimal interface with focus on the meme and rating
- **Accessibility**: Full keyboard navigation, proper ARIA labels, high contrast
- **Responsiveness**: Mobile-first design that works on all screen sizes
- **Performance**: Minimal JavaScript, fast loading times
- **Consistency**: shadcn/ui components provide consistent design language
