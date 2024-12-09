# src/queue/manager.py

import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import uuid

@dataclass
class QueueConfig:
    """Configuration for queue priorities and timeouts"""
    DEFAULT_PRIORITY = 1
    HIGH_PRIORITY = 2
    CRITICAL_PRIORITY = 3
    PROCESSING_TIMEOUT = 3600  # 1 hour in seconds
    RETRY_DELAY = 300         # 5 minutes in seconds
    MAX_RETRIES = 3

class QueueManager:
    """
    Manages distributed task queues for Reddit data collection and analysis.
    Uses Redis for reliable message queuing with priority support and error handling.
    """
    
    def __init__(self, redis_config: dict):
        """
        Initialize queue manager with Redis connection.
        
        Args:
            redis_config: Dictionary containing Redis connection parameters
                        (host, port, db, password if needed)
        """
        self.redis_client = redis.Redis(**redis_config)
        self.logger = logging.getLogger(__name__)
        
        # Define queue names for different tasks
        self.queues = {
            'subreddit_collection': 'queue:subreddits',
            'post_collection': 'queue:posts',
            'comment_collection': 'queue:comments',
            'sentiment_analysis': 'queue:sentiment',
            'failed_tasks': 'queue:failed',
            'processing': 'set:processing',
            'completed': 'set:completed'
        }

    def enqueue_subreddit(self, subreddit: str, start_date: datetime,
                         end_date: datetime, priority: int = QueueConfig.DEFAULT_PRIORITY) -> str:
        """
        Add a subreddit to the collection queue.
        
        Args:
            subreddit: Name of the subreddit to collect
            start_date: Start date for data collection
            end_date: End date for data collection
            priority: Task priority level
            
        Returns:
            task_id: Unique identifier for the queued task
        """
        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'type': 'subreddit_collection',
            'subreddit': subreddit,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'priority': priority,
            'attempts': 0,
            'enqueued_at': datetime.utcnow().isoformat()
        }
        
        # Store task details in a hash
        self.redis_client.hset(f'task:{task_id}', mapping=task)
        
        # Add to priority queue
        self.redis_client.zadd(
            self.queues['subreddit_collection'],
            {task_id: priority}
        )
        
        self.logger.info(f"Enqueued subreddit collection task: {task_id} for r/{subreddit}")
        return task_id

    def enqueue_posts_for_comments(self, post_ids: List[str],
                                 priority: int = QueueConfig.DEFAULT_PRIORITY) -> List[str]:
        """
        Add posts to the comment collection queue.
        
        Args:
            post_ids: List of post IDs to collect comments from
            priority: Task priority level
            
        Returns:
            task_ids: List of unique identifiers for the queued tasks
        """
        task_ids = []
        
        for post_id in post_ids:
            task_id = str(uuid.uuid4())
            task = {
                'id': task_id,
                'type': 'comment_collection',
                'post_id': post_id,
                'priority': priority,
                'attempts': 0,
                'enqueued_at': datetime.utcnow().isoformat()
            }
            
            # Store task details
            self.redis_client.hset(f'task:{task_id}', mapping=task)
            
            # Add to priority queue
            self.redis_client.zadd(
                self.queues['comment_collection'],
                {task_id: priority}
            )
            
            task_ids.append(task_id)
            
        self.logger.info(f"Enqueued {len(post_ids)} posts for comment collection")
        return task_ids

    def get_next_task(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the highest priority task from the specified queue.
        
        Args:
            queue_name: Name of the queue to pull from
            
        Returns:
            task: Dictionary containing task details or None if queue is empty
        """
        # Get highest priority task ID
        task_id = self.redis_client.zrevrange(
            self.queues[queue_name],
            0, 0,  # Get the first item only
            withscores=False
        )
        
        if not task_id:
            return None
            
        task_id = task_id[0].decode('utf-8')
        
        # Get task details
        task = self.redis_client.hgetall(f'task:{task_id}')
        if not task:
            return None
            
        # Convert bytes to string
        task = {k.decode('utf-8'): v.decode('utf-8') for k, v in task.items()}
        
        # Check if task is already being processed
        if self.redis_client.sismember(self.queues['processing'], task_id):
            # Check for timeout
            processing_time = self.redis_client.get(f'processing:{task_id}')
            if processing_time:
                start_time = datetime.fromisoformat(processing_time.decode('utf-8'))
                if datetime.utcnow() - start_time > timedelta(seconds=QueueConfig.PROCESSING_TIMEOUT):
                    # Task has timed out, reset it
                    self.handle_failed_task(task_id, task, "Task processing timeout")
                    self.redis_client.srem(self.queues['processing'], task_id)
                    self.redis_client.delete(f'processing:{task_id}')
                else:
                    return None
            
        # Mark task as processing
        self.redis_client.sadd(self.queues['processing'], task_id)
        self.redis_client.set(
            f'processing:{task_id}',
            datetime.utcnow().isoformat()
        )
        
        # Remove from queue
        self.redis_client.zrem(self.queues[queue_name], task_id)
        
        return task

    def complete_task(self, task_id: str, task: Dict[str, Any]) -> None:
        """
        Mark a task as completed and clean up its resources.
        
        Args:
            task_id: Unique identifier of the completed task
            task: Task details dictionary
        """
        # Remove from processing set
        self.redis_client.srem(self.queues['processing'], task_id)
        self.redis_client.delete(f'processing:{task_id}')
        
        # Add to completed set
        self.redis_client.sadd(self.queues['completed'], task_id)
        
        # Update task status
        task['completed_at'] = datetime.utcnow().isoformat()
        self.redis_client.hset(f'task:{task_id}', mapping=task)
        
        self.logger.info(f"Completed task: {task_id}")

    def handle_failed_task(self, task_id: str, task: Dict[str, Any],
                          error: str) -> None:
        """
        Handle a failed task by either retrying or moving to failed queue.
        
        Args:
            task_id: Unique identifier of the failed task
            task: Task details dictionary
            error: Error message describing the failure
        """
        attempts = int(task.get('attempts', 0))
        task['attempts'] = str(attempts + 1)
        task['last_error'] = error
        task['failed_at'] = datetime.utcnow().isoformat()
        
        if attempts < QueueConfig.MAX_RETRIES:
            # Requeue with delay and increased priority
            task['priority'] = str(min(
                int(task.get('priority', QueueConfig.DEFAULT_PRIORITY)) + 1,
                QueueConfig.CRITICAL_PRIORITY
            ))
            
            # Store updated task details
            self.redis_client.hset(f'task:{task_id}', mapping=task)
            
            # Add back to original queue with delay
            self.redis_client.zadd(
                self.queues[task['type']],
                {task_id: float(task['priority'])},
                nx=True
            )
            
            self.logger.warning(
                f"Task {task_id} failed, attempt {attempts + 1}/{QueueConfig.MAX_RETRIES}: {error}"
            )
        else:
            # Move to failed queue
            self.redis_client.zadd(
                self.queues['failed_tasks'],
                {task_id: float(task['priority'])}
            )
            self.logger.error(f"Task {task_id} failed permanently: {error}")

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all queues.
        
        Returns:
            Dictionary containing queue statistics
        """
        stats = {}
        
        for queue_type, queue_name in self.queues.items():
            if queue_type in ['processing', 'completed']:
                # Set-based queues
                stats[queue_type] = self.redis_client.scard(queue_name)
            else:
                # Sorted set queues
                stats[queue_type] = self.redis_client.zcard(queue_name)
        
        return stats

    def clear_queues(self) -> None:
        """Clear all queues (useful for testing or resetting)"""
        for queue_name in self.queues.values():
            self.redis_client.delete(queue_name)