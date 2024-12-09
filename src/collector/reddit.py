# reddit_collector.py
import praw
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Generator, Optional, Dict
from prawcore.exceptions import PrawcoreException

class RedditCollector:
   def __init__(self, config, db_handler):
       """Initialize Reddit collector with recovery support"""
       self.worker_id = str(uuid.uuid4())
       self.reddit = praw.Reddit(
           client_id=config.client_id,
           client_secret=config.client_secret,
           username=config.username,
           password=config.password,
           user_agent=config.user_agent
       )
       self.db = db_handler
       self.logger = logging.getLogger(__name__)

   def get_collection_progress(self, subreddit_name: str) -> Optional[Dict]:
       """Get the last processed position for this subreddit"""
       with self.db.get_connection() as conn:
           with conn.cursor() as cur:
               cur.execute("""
                   SELECT last_collected_timestamp, last_post_id
                   FROM collection_progress
                   WHERE subreddit_name = %s
                   ORDER BY updated_at DESC
                   LIMIT 1
               """, (subreddit_name,))
               result = cur.fetchone()
               if result:
                   return {
                       'timestamp': result[0],
                       'post_id': result[1]
                   }
               return None

   def update_progress(self, subreddit_name: str, 
                      timestamp: datetime, post_id: str):
       """Update collection progress"""
       with self.db.get_connection() as conn:
           with conn.cursor() as cur:
               cur.execute("""
                   INSERT INTO collection_progress (
                       subreddit_name, last_collected_timestamp,
                       last_post_id, status, worker_id, started_at
                   ) VALUES (%s, %s, %s, 'in_progress', %s, %s)
                   ON CONFLICT (subreddit_name, worker_id) 
                   DO UPDATE SET
                       last_collected_timestamp = EXCLUDED.last_collected_timestamp,
                       last_post_id = EXCLUDED.last_post_id,
                       updated_at = CURRENT_TIMESTAMP
               """, (
                   subreddit_name, timestamp, post_id,
                   self.worker_id, datetime.utcnow()
               ))

   def collect_subreddit_posts(self, subreddit_name: str,
                             start_date: datetime,
                             end_date: datetime,
                             batch_size: int = 100) -> None:
       """Collect posts with recovery support"""
       try:
           subreddit = self.reddit.subreddit(subreddit_name)
           subreddit_id = self.db.ensure_subreddit(subreddit_name)
           
           # Check for previous progress
           progress = self.get_collection_progress(subreddit_name)
           if progress:
               start_date = max(start_date, progress['timestamp'])

           posts_batch = []
           
           for post in subreddit.new(limit=None):
               post_date = datetime.fromtimestamp(post.created_utc)
               
               if start_date <= post_date <= end_date:
                   posts_batch.append({
                       'id': post.id,
                       'subreddit_id': subreddit_id,
                       'author': str(post.author) if post.author else '[deleted]',
                       'title': post.title,
                       'content': post.selftext,
                       'created_utc': post_date,
                       'score': post.score,
                       'upvote_ratio': post.upvote_ratio,
                       'is_deleted': post.selftext == '[deleted]'
                   })
                   
                   # Update progress after each post
                   self.update_progress(subreddit_name, post_date, post.id)
                   
                   # Process batch if size reached
                   if len(posts_batch) >= batch_size:
                       self.db.batch_insert_posts(posts_batch)
                       self.collect_comments_for_posts(posts_batch)
                       posts_batch = []
                       
               elif post_date < start_date:
                   break
               
               time.sleep(1)  # Respect rate limits
               
           # Process remaining posts
           if posts_batch:
               self.db.batch_insert_posts(posts_batch)
               self.collect_comments_for_posts(posts_batch)
               
       except Exception as e:
           self.logger.error(f"Error collecting {subreddit_name}: {str(e)}")
           raise

   def collect_comments_for_posts(self, posts: list) -> None:
       """Collect comments for a batch of posts"""
       for post in posts:
           try:
               comments_batch = []
               submission = self.reddit.submission(id=post['id'])
               submission.comments.replace_more(limit=None)
               
               for comment in self._traverse_comments(submission.comments):
                   comments_batch.append({
                       'id': comment.id,
                       'post_id': post['id'],
                       'parent_comment_id': comment.parent_id.split('_')[1]
                           if comment.parent_id.startswith('t1_') else None,
                       'author': str(comment.author) if comment.author else '[deleted]',
                       'content': comment.body,
                       'created_utc': datetime.fromtimestamp(comment.created_utc),
                       'score': comment.score,
                       'is_deleted': comment.body == '[deleted]'
                   })
                   
                   if len(comments_batch) >= 100:
                       self.db.batch_insert_comments(comments_batch)
                       comments_batch = []
                       
               if comments_batch:
                   self.db.batch_insert_comments(comments_batch)
                   
               time.sleep(1)  # Respect rate limits
                   
           except Exception as e:
               self.logger.error(f"Error collecting comments for post {post['id']}: {str(e)}")
               continue

   def _traverse_comments(self, comments, level=0) -> Generator:
       """Recursively traverse comment tree"""
       for comment in comments:
           yield comment
           if hasattr(comment, 'replies'):
               yield from self._traverse_comments(comment.replies, level + 1)
