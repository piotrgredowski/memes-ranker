-- Memes Ranker Database Schema
-- SQLite database schema for meme ranking application
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT
    ,name TEXT NOT NULL
    ,session_token TEXT UNIQUE NOT NULL
    ,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Memes table
CREATE TABLE memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT
    ,filename TEXT NOT NULL
    ,path TEXT NOT NULL
    ,active BOOLEAN DEFAULT TRUE
    ,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Rankings table
CREATE TABLE rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT
    ,user_id INTEGER NOT NULL
    ,meme_id INTEGER NOT NULL
    ,score INTEGER NOT NULL CHECK (
        score >= 0
        AND score <= 10
        )
    ,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ,FOREIGN KEY (user_id) REFERENCES users(id)
    ,FOREIGN KEY (meme_id) REFERENCES memes(id)
    ,UNIQUE (
        user_id
        ,meme_id
        )
    );

-- Sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT
    ,name TEXT NOT NULL
    ,start_time TIMESTAMP
    ,end_time TIMESTAMP
    ,active BOOLEAN DEFAULT FALSE
    ,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Results reveal table
CREATE TABLE results_reveal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    current_position INTEGER DEFAULT 0,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
    );

-- Indexes for better performance
CREATE INDEX idx_users_session_token ON users (session_token);

CREATE INDEX idx_rankings_user_id ON rankings (user_id);

CREATE INDEX idx_rankings_meme_id ON rankings (meme_id);

CREATE INDEX idx_memes_active ON memes (active);

CREATE INDEX idx_sessions_active ON sessions (active);

CREATE INDEX idx_results_reveal_session ON results_reveal (session_id);

CREATE UNIQUE INDEX idx_results_reveal_unique_session ON results_reveal (session_id);
