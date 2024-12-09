# config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
   host: str = os.getenv('DB_HOST', 'localhost')
   port: int = int(os.getenv('DB_PORT', 5432))
   dbname: str = os.getenv('DB_NAME', 'reddit_analyzer')
   user: str = os.getenv('DB_USER', 'postgres')
   password: str = os.getenv('DB_PASSWORD', '')
   max_connections: int = 10

@dataclass
class RedditConfig:
   client_id: str = os.getenv('REDDIT_CLIENT_ID', '')
   client_secret: str = os.getenv('REDDIT_CLIENT_SECRET', '')
   username: str = os.getenv('REDDIT_USERNAME', '')
   password: str = os.getenv('REDDIT_PASSWORD', '')
   user_agent: str = f"Script/1.0 (by /u/{os.getenv('REDDIT_USERNAME', '')})"

@dataclass
class RedisConfig:
   host: str = os.getenv('REDIS_HOST', 'localhost')
   port: int = int(os.getenv('REDIS_PORT', 6379))
   db: int = int(os.getenv('REDIS_DB', 0))

class Config:
   def __init__(self):
       self.database = DatabaseConfig()
       self.reddit = RedditConfig()
       self.redis = RedisConfig()