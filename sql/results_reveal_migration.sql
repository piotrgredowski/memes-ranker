-- Results Reveal Feature Migration
-- Add results_reveal table to track reveal progress for each session

-- Create results_reveal table
CREATE TABLE results_reveal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    current_position INTEGER DEFAULT 0,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Add index for performance
CREATE INDEX idx_results_reveal_session ON results_reveal(session_id);

-- Add unique constraint to ensure one reveal per session
CREATE UNIQUE INDEX idx_results_reveal_unique_session ON results_reveal(session_id);
