# run_analyzer.py
import argparse
import logging
import time
from datetime import datetime
from src.config import Config
from src.db.handler import DatabaseHandler
from src.analysis.metrics.sentiment import SentimentAnalyzer

def setup_logging():
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('sentiment_analyzer.log'),
           logging.StreamHandler()
       ]
   )

def run_analyzer(batch_size: int, sleep_time: int):
   """Run continuous sentiment analysis"""
   config = Config()
   db_handler = DatabaseHandler(config.database)
   analyzer = SentimentAnalyzer(db_handler)
   
   logging.info(f"Starting sentiment analysis with batch size {batch_size}")
   
   while True:
       try:
           analyzer.process_batch(batch_size)
           time.sleep(sleep_time)  # Wait between batches
           
       except Exception as e:
           logging.error(f"Analyzer error: {str(e)}")
           time.sleep(sleep_time * 2)  # Wait longer after error

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description='Reddit Sentiment Analyzer')
   parser.add_argument('--batch-size', type=int, default=100,
                      help='Number of items to process in each batch')
   parser.add_argument('--sleep-time', type=int, default=5,
                      help='Seconds to sleep between batches')
   
   args = parser.parse_args()
   
   setup_logging()
   run_analyzer(args.batch_size, args.sleep_time)
