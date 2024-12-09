# sentiment.py
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
from datetime import datetime
from typing import Dict, List

class SentimentAnalyzer:
   def __init__(self, db_handler):
       """Initialize sentiment analyzer with database connection"""
       self.analyzer = SentimentIntensityAnalyzer()
       self.db = db_handler
       self.logger = logging.getLogger(__name__)

   def get_unprocessed_content(self, batch_size: int = 100) -> List[Dict]:
       """Get content that hasn't been analyzed yet"""
       with self.db.get_connection() as conn:
           with conn.cursor() as cur:
               cur.execute("""
                   SELECT 
                       CASE 
                           WHEN p.id IS NOT NULL THEN 'post'
                           ELSE 'comment'
                       END as content_type,
                       COALESCE(p.id, c.id) as content_id,
                       COALESCE(p.content, c.content) as content
                   FROM (
                       SELECT id, content FROM posts 
                       WHERE id NOT IN (SELECT content_id FROM content_sentiment)
                       LIMIT %(batch_size)s
                   ) p
                   FULL OUTER JOIN (
                       SELECT id, content FROM comments 
                       WHERE id NOT IN (SELECT content_id FROM content_sentiment)
                       LIMIT %(batch_size)s
                   ) c ON FALSE
               """, {'batch_size': batch_size})
               
               return [
                   {
                       'content_type': row[0],
                       'content_id': row[1],
                       'content': row[2]
                   }
                   for row in cur.fetchall()
               ]

   def store_sentiment(self, content_id: str, content_type: str,
                      scores: Dict[str, float]) -> None:
       """Store sentiment analysis results"""
       with self.db.get_connection() as conn:
           with conn.cursor() as cur:
               cur.execute("""
                   INSERT INTO content_sentiment (
                       content_id,
                       content_type,
                       compound_score,
                       positive_score,
                       neutral_score,
                       negative_score
                   ) VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (content_id) DO NOTHING
               """, (
                   content_id,
                   content_type,
                   scores['compound'],
                   scores['pos'],
                   scores['neu'],
                   scores['neg']
               ))

   def analyze_content(self, text: str) -> Dict[str, float]:
       """Analyze text content for sentiment scores"""
       if not text or text == '[deleted]':
           return {
               'compound': 0.0,
               'pos': 0.0,
               'neu': 1.0,
               'neg': 0.0
           }
       
       return self.analyzer.polarity_scores(text)

   def process_batch(self, batch_size: int = 100) -> None:
       """Process a batch of content for sentiment analysis"""
       try:
           content_batch = self.get_unprocessed_content(batch_size)
           
           for content in content_batch:
               try:
                   sentiment_scores = self.analyze_content(content['content'])
                   self.store_sentiment(
                       content['content_id'],
                       content['content_type'],
                       sentiment_scores
                   )
               except Exception as e:
                   self.logger.error(
                       f"Error analyzing content {content['content_id']}: {str(e)}"
                   )
                   continue
                   
       except Exception as e:
           self.logger.error(f"Batch processing error: {str(e)}")
           raise
