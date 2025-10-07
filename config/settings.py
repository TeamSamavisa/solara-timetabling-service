import os
from typing import Dict, Any


def get_rabbitmq_config() -> Dict[str, Any]:
    """Get RabbitMQ configuration from environment variables"""
    return {
        "host": os.getenv("RABBITMQ_HOST", "localhost"),
        "port": int(os.getenv("RABBITMQ_PORT", 5672)),
        "vhost": os.getenv("RABBITMQ_VHOST", "/"),
        "username": os.getenv("RABBITMQ_USERNAME", "guest"),
        "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
        "queue_name": os.getenv("RABBITMQ_QUEUE", "allocation"),
        "heartbeat": int(os.getenv("RABBITMQ_HEARTBEAT", 600)),
        "connection_attempts": int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", 3)),
        "retry_delay": int(os.getenv("RABBITMQ_RETRY_DELAY", 5)),
    }


def get_app_config() -> Dict[str, Any]:
    """Get application configuration from environment variables"""
    return {
        "debug": os.getenv("DEBUG", "False").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }
