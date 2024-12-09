"""
Basic plotting functionality for Reddit analysis using matplotlib and seaborn.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Optional, Tuple
import pandas as pd
from ..base import BaseAnalyzer

class AnalysisPlotter(BaseAnalyzer):
    """Creates static plots for analysis results"""
    
    def __init__(self, db_handler):
        super().__init__(db_handler)
        self.setup_style()

    def setup_style(self):
        """Configure plotting style"""
        plt.style.use('seaborn')
        sns.set_palette("husl")
        plt.rcParams['figure.figsize'] = (12, 8)

    def plot_engagement_metrics(self, data: pd.DataFrame,
                              metric: str = 'score') -> plt.Figure:
        """Plot engagement metrics over time"""
        fig, ax = plt.subplots()
        sns.lineplot(data=data, x='created_utc', y=metric, ax=ax)
        ax.set_title(f'{metric.title()} Over Time')
        ax.set_xlabel('Date')
        ax.set_ylabel(metric.title())
        plt.xticks(rotation=45)
        return fig

    def plot_sentiment_distribution(self, data: pd.DataFrame) -> plt.Figure:
        """Plot distribution of sentiment scores"""
        fig, ax = plt.subplots()
        sns.histplot(data=data, x='compound_score', bins=50, ax=ax)
        ax.set_title('Sentiment Score Distribution')
        ax.set_xlabel('Compound Sentiment Score')
        ax.set_ylabel('Count')
        return fig

    def plot_user_activity(self, data: pd.DataFrame) -> plt.Figure:
        """Plot user activity patterns"""
        fig, ax = plt.subplots()
        sns.heatmap(data, cmap='YlOrRd', ax=ax)
        ax.set_title('User Activity Heatmap')
        return fig

    def plot_topic_trends(self, data: pd.DataFrame) -> plt.Figure:
        """Plot topic popularity trends"""
        fig, ax = plt.subplots()
        sns.barplot(data=data, x='topic', y='frequency', ax=ax)
        ax.set_title('Top Topics')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return fig

    def save_plot(self, fig: plt.Figure, filename: str) -> None:
        """Save plot to file"""
        fig.savefig(filename, bbox_inches='tight', dpi=300)
