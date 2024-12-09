"""
Base analyzer class providing common functionality for all analysis components.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

class BaseAnalyzer:
    """Base class for all analysis components"""
    
    def __init__(self, db_handler):
        self.db = db_handler
        self.logger = logging.getLogger(__name__)

    def get_date_range_data(self, start_date: datetime, 
                           end_date: datetime, 
                           subreddit: Optional[str] = None) -> pd.DataFrame:
        """Get data for a specific date range"""
        query = """
            SELECT *
            FROM posts p
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE p.created_utc BETWEEN %s AND %s
            {subreddit_filter}
        """
        
        params = [start_date, end_date]
        subreddit_filter = ""
        
        if subreddit:
            subreddit_filter = "AND s.name = %s"
            params.append(subreddit)
            
        query = query.format(subreddit_filter=subreddit_filter)
        
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)
