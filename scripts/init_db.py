# init_db.py
import os
import psycopg2
from dotenv import load_dotenv

def init_db():
    # Load environment variables
    load_dotenv()
    
    # Default database connection for creating new database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'mm'),  # Using mm as default user
        password=os.getenv('DB_PASSWORD', '')
    )
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            # Create database if it doesn't exist
            cur.execute("SELECT 1 FROM pg_database WHERE datname='reddit_analyzer'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE reddit_analyzer")
                print("Created database: reddit_analyzer")
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        return
    finally:
        conn.close()

    # Connect to the reddit_analyzer database to create tables
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            dbname='reddit_analyzer',
            user=os.getenv('DB_USER', 'mm'),  # Using mm as default user
            password=os.getenv('DB_PASSWORD', '')
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Create tables
            cur.execute("""
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

                CREATE INDEX IF NOT EXISTS idx_posts_created_utc ON posts(created_utc);
                CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
                CREATE INDEX IF NOT EXISTS idx_collection_progress_worker ON collection_progress(worker_id);
            """)
            print("Successfully created all tables and indexes")
            
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
