# run_collector.py
import argparse
import logging
from datetime import datetime, timedelta
from src.config import Config
from src.collector.reddit import RedditCollector
from src.db.handler import DatabaseHandler

def setup_logging():
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('reddit_collector.log'),
           logging.StreamHandler()
       ]
   )

def run_collector(subreddits: list, start_date: datetime, end_date: datetime):
   """Run collector for specified subreddits"""
   config = Config()
   db_handler = DatabaseHandler(config.database)
   collector = RedditCollector(config.reddit, db_handler)
   
   for subreddit in subreddits:
       try:
           logging.info(f"Starting collection for r/{subreddit}")
           collector.collect_subreddit_posts(
               subreddit_name=subreddit,
               start_date=start_date,
               end_date=end_date,
               batch_size=100
           )
           logging.info(f"Completed collection for r/{subreddit}")
       except Exception as e:
           logging.error(f"Failed to collect r/{subreddit}: {str(e)}")

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description='Reddit Data Collector')
   parser.add_argument('--subreddits', nargs='+', required=True,
                      help='List of subreddits to process')
   parser.add_argument('--days', type=int, default=90,
                      help='Number of days to look back (default: 90)')
   parser.add_argument('--start-date', type=str,
                      help='Start date (YYYY-MM-DD) - overrides days parameter')
   parser.add_argument('--end-date', type=str,
                      help='End date (YYYY-MM-DD) - defaults to yesterday')
   
   args = parser.parse_args()
   
   setup_logging()
   
   # Calculate dates
   if args.start_date:
       start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
   else:
       start_date = datetime.utcnow() - timedelta(days=args.days)
       
   if args.end_date:
       end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
   else:
       end_date = datetime.utcnow() - timedelta(days=1)
   
   logging.info(f"Starting collection for subreddits: {args.subreddits}")
   logging.info(f"Date range: {start_date} to {end_date}")
   
   run_collector(args.subreddits, start_date, end_date)
