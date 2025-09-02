"""Celery application configuration for IT Glue MCP Server."""


from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from src.config.settings import settings

# Create Celery app
app = Celery(
    'itglue_mcp',
    broker=settings.REDIS_URL or 'redis://redis:6379/0',
    backend=settings.REDIS_URL or 'redis://redis:6379/0',
    include=[
        'src.tasks.sync_tasks',
        'src.tasks.embedding_tasks',
        'src.tasks.maintenance_tasks',
        'src.tasks.notification_tasks'
    ]
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },

    # Task execution settings
    task_track_started=True,
    task_time_limit=3600,  # Hard time limit of 1 hour
    task_soft_time_limit=3000,  # Soft time limit of 50 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Task routing
    task_routes={
        'src.tasks.sync_tasks.*': {'queue': 'sync'},
        'src.tasks.embedding_tasks.*': {'queue': 'embeddings'},
        'src.tasks.maintenance_tasks.*': {'queue': 'maintenance'},
        'src.tasks.notification_tasks.*': {'queue': 'notifications'},
    },

    # Queue configuration
    task_queues=(
        Queue('default', routing_key='default'),
        Queue('sync', routing_key='sync'),
        Queue('embeddings', routing_key='embeddings'),
        Queue('maintenance', routing_key='maintenance'),
        Queue('notifications', routing_key='notifications'),
    ),

    # Worker settings
    worker_pool='prefork',
    worker_concurrency=4,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',

    # Beat schedule for periodic tasks
    beat_schedule={
        # Full sync every night at 2 AM
        'nightly-full-sync': {
            'task': 'src.tasks.sync_tasks.full_sync',
            'schedule': crontab(hour=2, minute=0),
            'options': {
                'queue': 'sync',
                'priority': 5,
            }
        },
        # Incremental sync every 30 minutes
        'periodic-incremental-sync': {
            'task': 'src.tasks.sync_tasks.incremental_sync',
            'schedule': crontab(minute='*/30'),
            'options': {
                'queue': 'sync',
                'priority': 3,
            }
        },
        # Update embeddings for new content every hour
        'hourly-embedding-update': {
            'task': 'src.tasks.embedding_tasks.update_embeddings',
            'schedule': crontab(minute=0),
            'options': {
                'queue': 'embeddings',
                'priority': 2,
            }
        },
        # Clean up old cache entries every 6 hours
        'cache-cleanup': {
            'task': 'src.tasks.maintenance_tasks.cleanup_cache',
            'schedule': crontab(hour='*/6', minute=0),
            'options': {
                'queue': 'maintenance',
                'priority': 1,
            }
        },
        # Database maintenance daily at 3 AM
        'database-maintenance': {
            'task': 'src.tasks.maintenance_tasks.database_maintenance',
            'schedule': crontab(hour=3, minute=0),
            'options': {
                'queue': 'maintenance',
                'priority': 1,
            }
        },
        # Check system health every 5 minutes
        'health-check': {
            'task': 'src.tasks.maintenance_tasks.health_check',
            'schedule': crontab(minute='*/5'),
            'options': {
                'queue': 'maintenance',
                'priority': 0,
            }
        },
    },

    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Configure Celery to use UTC
app.conf.timezone = 'UTC'

if __name__ == '__main__':
    app.start()
