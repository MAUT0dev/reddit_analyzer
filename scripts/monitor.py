# monitor.py
import logging
from datetime import datetime, timedelta
from reddit_analyzer.src.config import Config
from reddit_analyzer.src.db.handler import DatabaseHandler

def monitor_collectors():
   """Monitor active collectors and their progress"""
   config = Config()
   db_handler = DatabaseHandler(config.database)
   
   with db_handler.get_connection() as conn:
       with conn.cursor() as cur:
           # Get active collectors
           cur.execute("""
               SELECT 
                   subreddit_name,
                   worker_id,
                   last_collected_timestamp,
                   status,
                   started_at,
                   updated_at
               FROM collection_progress
               WHERE updated_at > NOW() - INTERVAL '1 hour'
               ORDER BY updated_at DESC
           """)
           
           active_collectors = cur.fetchall()
           
           print("\nActive Collectors:")
           for collector in active_collectors:
               print(f"""
Subreddit: {collector[0]}
Worker ID: {collector[1]}
Last Collection: {collector[2]}
Status: {collector[3]}
Started: {collector[4]}
Last Update: {collector[5]}
------------------------""")
           
           # Get collection statistics
           cur.execute("""
               SELECT 
                   s.name as subreddit,
                   COUNT(DISTINCT p.id) as post_count,
                   COUNT(DISTINCT c.id) as comment_count,
                   MAX(p.created_utc) as latest_post,
                   MIN(p.created_utc) as earliest_post
               FROM subreddits s
               LEFT JOIN posts p ON s.id = p.subreddit_id
               LEFT JOIN comments c ON p.id = c.post_id
               GROUP BY s.name
               ORDER BY s.name
           """)
           
           stats = cur.fetchall()
           
           print("\nCollection Statistics:")
           for stat in stats:
               print(f"""
Subreddit: {stat[0]}
Posts: {stat[1]}
Comments: {stat[2]}
Date Range: {stat[4]} to {stat[3]}
------------------------""")

if __name__ == "__main__":
   monitor_collectors()
