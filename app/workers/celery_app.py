from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "complaint_processor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.document_tasks",
        "app.workers.tasks.summary_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
    result_expires=86400,  # Results expire after 24 hours

    # Task routes for different queues
    task_routes={
        "app.workers.tasks.document_tasks.*": {"queue": "documents"},
        "app.workers.tasks.summary_tasks.*": {"queue": "summaries"},
    },

    # Retry configuration
    task_annotations={
        "*": {
            "rate_limit": "10/m",  # 10 tasks per minute
            "max_retries": 3,
            "default_retry_delay": 60,
        }
    }
)
