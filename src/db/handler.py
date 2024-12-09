# db_handler.py
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_batch
from contextlib import contextmanager
import logging
from datetime import datetime
from ..config import DatabaseConfig

class DatabaseHandler:
   def __init__(self, config: DatabaseConfig):
       self.config = config
       self.connection_pool = psycopg2.pool.SimpleConnectionPool(
           minconn=1,
           maxconn=config.max_connections,
           host=config.host,
           port=config.port,
           dbname=config.dbname,
           user=config.user,
           password=config.password
       )
       self.logger = logging.getLogger(__name__)

   @contextmanager
   def get_connection(self):
       conn = self.connection_pool.getconn()
       try:
           yield conn
           conn.commit()
       except Exception as e:
           conn.rollback()
           self.logger.error(f"Database error: {str(e)}")
           raise
       finally:
           self.connection_pool.putconn(conn)

   def ensure_subreddit(self, subreddit_name: str) -> int:
       with self.get_connection() as conn:
           with conn.cursor() as cur:
               cur.execute("""
                   INSERT INTO subreddits (name)
                   VALUES (%s)
                   ON CONFLICT (name) DO UPDATE
                       SET name = EXCLUDED.name
                   RETURNING id
               """, (subreddit_name,))
               return cur.fetchone()[0]

   def batch_insert_posts(self, posts: list) -> None:
       if not posts:
           return
           
       insert_query = """
           INSERT INTO posts (
               id, subreddit_id, author, title, content,
               created_utc, score, upvote_ratio, is_deleted
           ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET
               score = EXCLUDED.score,
               upvote_ratio = EXCLUDED.upvote_ratio,
               is_deleted = EXCLUDED.is_deleted,
               last_updated = CURRENT_TIMESTAMP
       """
       
       with self.get_connection() as conn:
           with conn.cursor() as cur:
               execute_batch(
                   cur,
                   insert_query,
                   [(
                       post['id'],
                       post['subreddit_id'],
                       post['author'],
                       post['title'],
                       post['content'],
                       post['created_utc'],
                       post['score'],
                       post['upvote_ratio'],
                       post['is_deleted']
                   ) for post in posts],
                   page_size=1000
               )

   def batch_insert_comments(self, comments: list) -> None:
       if not comments:
           return
           
       insert_query = """
           INSERT INTO comments (
               id, post_id, parent_comment_id, author,
               content, created_utc, score, is_deleted
           ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET
               score = EXCLUDED.score,
               is_deleted = EXCLUDED.is_deleted,
               last_updated = CURRENT_TIMESTAMP
       """
       
       with self.get_connection() as conn:
           with conn.cursor() as cur:
               execute_batch(
                   cur,
                   insert_query,
                   [(
                       comment['id'],
                       comment['post_id'],
                       comment['parent_comment_id'],
                       comment['author'],
                       comment['content'],
                       comment['created_utc'],
                       comment['score'],
                       comment['is_deleted']
                   ) for comment in comments],
                   page_size=1000
               )
