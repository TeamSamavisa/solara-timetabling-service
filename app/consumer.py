import json
import logging
import pika
import time

from config.settings import get_rabbitmq_config

logger = logging.getLogger(__name__)


def callback(ch, method, properties, body):
    """Message callback - acknowledges quickly and processes asynchronously"""
    correlation_id = properties.correlation_id

    try:
        logger.info(f"Received message: {correlation_id}")
        message = json.loads(body)
        command = message.get("pattern")

        if command == "test_connection":
            result = {"status": "success", "message": "Connection established"}

            # Send response and acknowledge immediately
            if properties.reply_to:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=correlation_id),
                    body=json.dumps(result),
                )

        else:
            result = {"status": "error", "message": f"Unknown command: {command}"}

            if properties.reply_to:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=correlation_id),
                    body=json.dumps(result),
                )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in callback: {e}", exc_info=True)

    finally:
        # Acknowledge the message (except for process_assignments which is handled above)
        try:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.warning(f"Error acknowledging message: {e}")


def create_connection_and_channel(rabbitmq_config):
    """Create RabbitMQ connection and channel with proper configuration"""
    connection_params = pika.ConnectionParameters(
        host=rabbitmq_config["host"],
        port=rabbitmq_config["port"],
        virtual_host=rabbitmq_config["vhost"],
        credentials=pika.PlainCredentials(
            username=rabbitmq_config["username"], password=rabbitmq_config["password"]
        ),
        heartbeat=rabbitmq_config["heartbeat"],
        blocked_connection_timeout=300,
        socket_timeout=10,
        connection_attempts=3,
        retry_delay=2,
    )

    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()

    # Configure channel
    queue_name = rabbitmq_config["queue_name"]
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    return connection, channel, queue_name


def start_consumer():
    """Start the RabbitMQ consumer with improved reconnection logic"""
    rabbitmq_config = get_rabbitmq_config()
    max_reconnect_attempts = 10
    reconnect_delay = 5
    current_attempt = 0

    while current_attempt < max_reconnect_attempts:
        connection = None
        channel = None

        try:
            logger.info(
                f"Starting consumer (attempt {current_attempt + 1}/{max_reconnect_attempts})"
            )

            connection, channel, queue_name = create_connection_and_channel(
                rabbitmq_config
            )

            # Reset attempt counter on successful connection
            current_attempt = 0

            channel.basic_consume(queue=queue_name, on_message_callback=callback)

            logger.info(f"Consumer started, listening on queue: {queue_name}")
            channel.start_consuming()

        except pika.exceptions.StreamLostError as e:
            logger.error(
                f"Connection lost: {e}. Attempt {current_attempt + 1}/{max_reconnect_attempts}"
            )
            current_attempt += 1

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(
                f"AMQP Connection error: {e}. Attempt {current_attempt + 1}/{max_reconnect_attempts}"
            )
            current_attempt += 1

        except KeyboardInterrupt:
            logger.info("Shutdown signal received, stopping consumer...")
            break

        except Exception as e:
            logger.error(
                f"Unexpected error: {e}. Attempt {current_attempt + 1}/{max_reconnect_attempts}",
                exc_info=True,
            )
            current_attempt += 1

        finally:
            # Clean up connections
            try:
                if channel and not channel.is_closed:
                    channel.stop_consuming()
                    channel.close()
            except Exception as e:
                logger.warning(f"Error closing channel: {e}")

            try:
                if connection and not connection.is_closed:
                    connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

        if current_attempt < max_reconnect_attempts:
            logger.info(f"Reconnecting in {reconnect_delay} seconds...")
            time.sleep(reconnect_delay)
            # Exponential backoff with max delay of 60 seconds
            reconnect_delay = min(reconnect_delay * 1.5, 60)

    logger.error(
        f"Max reconnection attempts ({max_reconnect_attempts}) reached. Exiting."
    )


if __name__ == "__main__":
    start_consumer()
