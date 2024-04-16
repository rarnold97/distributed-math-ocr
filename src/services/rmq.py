from __future__ import annotations

from services.logger import logger
from services import LOCAL_MODE

import pika
from pika.channel import Channel
from pika.connection import Connection
from pika.credentials import PlainCredentials
from google.protobuf.message import Message


def get_rmq_connection_parameters(localmode: bool = False) -> pika.ConnectionParameters:
    if localmode:
        return pika.ConnectionParameters(host = 'localhost')

    # TODO - change host to static IP generated in docker-compose
    return pika.ConnectionParameters(
        host = 'localhost',
        port = 5672,
        connection_attempts = 10,
        credentials = PlainCredentials(username = "admin", password = "admin"))

def publish_proto_message(message: Message, queue_name: str):
    connection: Connection = pika.BlockingConnection(
        get_rmq_connection_parameters(LOCAL_MODE))
    channel: Channel = connection.channel()
    channel.queue_declare(queue = queue_name, durable = True)
    channel.basic_publish(
        exchange = '',
        routing_key = queue_name,
        properties = pika.BasicProperties(delivery_mode = pika.DeliveryMode.Persistent),
        body = message.SerializeToString())
    logger.info(f" [x] Sent Protobuf Message to queue: {queue_name}. Message Contents:\n{message}")
    connection.close()
