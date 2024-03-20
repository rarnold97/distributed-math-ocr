from __future__ import annotations

from multiprocessing import Process
import sys, os, time
from dataclasses import dataclass
from typing import Callable, TypeAlias
from itertools import chain
import enum

import pika
from pika.channel import Channel
from pika.spec import BasicProperties
from pika.spec import Basic
DeliveryProperties: TypeAlias = Basic.Deliver
ConsumerCallbackSignature: TypeAlias = Callable[[Channel, DeliveryProperties, BasicProperties, bytes], None]


class RabbitMQConnection:
    EXCHANGE_KEY: str = ''
    
    def __init__(self, queue_name: str):
        self._queue_name = queue_name
        
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        # The durable key tells rabbitMQ that the queue should survive a shutdown of RabbitMQ
        self.channel.queue_declare(queue = self._queue_name, durable=True)

class RabbitMQProducer(RabbitMQConnection):
    def __init__(self, queue_name: str):
        super().__init__(queue_name)
    
    def publish(self, message: bytes):
        self.channel.basic_publish(exchange = RabbitMQConnection.EXCHANGE_KEY,
                                    routing_key = self._queue_name,
                                    body = message,
                                    properties = pika.BasicProperties(
                                        delivery_mode=pika.DeliveryMode.Persistent))
        
    def __enter__(self) -> RabbitMQProducer:
        return self
    
    def __exit__(self, execute_type, execute_value, execute_traceback):
        self.connection.close()


class RabbitMQConsumer(RabbitMQConnection):
    def __init__(self, queue_name: str, consume_callback: ConsumerCallbackSignature):
        super().__init__(queue_name)
        self._consume_message_callback = consume_callback
        # see : https://www.rabbitmq.com/tutorials/tutorial-two-python#fair-dispatch
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self._queue_name,
                                   on_message_callback=self._consume_message_callback)
    
    def consume(self):
        self.channel.start_consuming()


def run_interruptable(process_spawn_func: Callable):
    def wrapper():
        try:
            process_spawn_func()
        except KeyboardInterrupt:
            print("\nTERMINATING PROGRAM!!!!!!!!!!!!!!!!!!")
            try:
                sys.exit(0)
            except:
                os._exit(0)
    return wrapper

# HELLO WORLD EXAMPLE
# ------------------------------------------------------------------------------
def hello_world_send():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='hello')
    channel.basic_publish(exchange='', routing_key='hello', body='Hello World!')
    print(' [x] Sent "Hello World!"')
    connection.close()

def hello_world_receive():

    def callback(channel, method, properties, body):
        print(f" [x] Received {body}")

    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='hello')
    channel.basic_consume(queue='hello', auto_ack=True, on_message_callback=callback)
    print(" [*] Waiting for messages")
    channel.start_consuming()

@run_interruptable
def hello_world_example():
    receive_process = Process(target=hello_world_receive)
    receive_process.start()
    time.sleep(1)
    send_process = Process(target=hello_world_send)
    send_process.start()
    time.sleep(1)

    receive_process.join()
    send_process.join()

# ------------------------------------------------------------------------------
# WORKER QUEUE EXAMPLE
def worker_queue_send(message_contents: str|None = None):
    with RabbitMQProducer(queue_name="task_queue") as publisher:
        publisher.publish(message_contents)
        print(f" [x] Sent {message_contents}")

def worker_queue_receive():

    def callback(channel: Channel, method: DeliveryProperties, properties: BasicProperties, body: bytes):
        print(f" [x] Received {body.decode()}")
        time.sleep(body.count(b'.'))
        print(" [x] Done")
        channel.basic_ack(delivery_tag = method.delivery_tag)

    subscriber = RabbitMQConsumer(queue_name = "task_queue", consume_callback=callback)
    print(" [*] Waiting for messages")
    subscriber.consume()

@run_interruptable
def worker_queue_example():
    workers = (
        Process(target=worker_queue_receive),
        Process(target=worker_queue_receive))
    for worker in workers:
        worker.start()

    time.sleep(1)
    senders = (
        Process(target=worker_queue_send, args=('First message.',)),
        Process(target=worker_queue_send, args=('Second message..',)),
        Process(target=worker_queue_send, args=('Third message...',)),
        Process(target=worker_queue_send, args=('Fourth message....',)),
        Process(target=worker_queue_send, args=('Fifth message.....',)))
    for sender in senders:
        sender.start()

    for process in chain(workers, senders):
        process.join()

if __name__ == "__main__":
    # UNCOMMENT SPECIFIC FUNCTION TO SEE EXAMPLE IN ACTION!
    #hello_world_example()
    worker_queue_example()

    pass