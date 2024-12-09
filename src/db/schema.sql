-- init.sql
CREATE DATABASE reddit_analyzer;

\c reddit_analyzer

CREATE TABLE IF NOT EXISTS subreddits (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    last_scan_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id VARCHAR(50) PRIMARY KEY,
    subreddit_id INTEGER REFERENCES subreddits(id),
    author VARCHAR(50),
    title TEXT,
    content TEXT,
    created_utc TIMESTAMP,
    score INTEGER,
    upvote_ratio FLOAT,
    is_deleted BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id VARCHAR(50) PRIMARY KEY,
    post_id VARCHAR(50) REFERENCES posts(id),
    parent_comment_id VARCHAR(50) REFERENCES comments(id),
    author VARCHAR(50),
    content TEXT,
    created_utc TIMESTAMP,
    score INTEGER,
    is_deleted BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_progress (
    id SERIAL PRIMARY KEY,
    subreddit_name VARCHAR(50),
    last_collected_timestamp TIMESTAMP,
    last_post_id VARCHAR(50),
    status VARCHAR(20),
    worker_id UUID,
    started_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subreddit_name, worker_id)
);

CREATE TABLE IF NOT EXISTS content_sentiment (
    id SERIAL PRIMARY KEY,
    content_id VARCHAR(50) NOT NULL,
    content_type VARCHAR(10) NOT NULL,
    compound_score FLOAT NOT NULL,
    positive_score FLOAT NOT NULL,
    neutral_score FLOAT NOT NULL,
    negative_score FLOAT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, content_type)
);

CREATE INDEX idx_posts_created_utc ON posts(created_utc);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_collection_progress_worker ON collection_progress(worker_id);
CREATE INDEX idx_content_sentiment_content ON content_sentiment(content_id, content_type);
