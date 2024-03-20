from __future__ import annotations

from typing import Callable, TypeAlias
import uuid

import pika
from pika.channel import Channel
from pika.spec import BasicProperties
from pika.spec import Basic
from pika.frame import Method as FrameMethod
DeliveryProperties: TypeAlias = Basic.Deliver
ConsumerCallbackSignature: TypeAlias = Callable[[Channel, DeliveryProperties, BasicProperties, bytes], None]

ML_REQUEST_QUEUE_NAME: str = "ml_pipeline"

class MLServerInterface:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost"))
        self.channel: Channel = self.connection.channel()
        self.channel.queue_declare(queue = ML_REQUEST_QUEUE_NAME)    

    def on_request(self, channel: Channel, method: BasicProperties,
                   properties: DeliveryProperties, message_body: bytes):
        request: bytes = message_body
        response: bytes = self.working_function(request)
        
        channel.basic_publish(exchange = '', routing_key = properties.reply_to,
                                   properties = pika.BasicProperties(
                                       correlation_id = properties.correlation_id),
                                   body = response)
        channel.basic_ack(delivery_tag = method.delivery_tag)
    
    def run(self):
        self.channel.basic_qos(prefetch_count = 1)
        self.channel.basic_consume(queue = ML_REQUEST_QUEUE_NAME,
                                   on_message_callback = self.on_request)
        try:
            print("Awaiting Machine Learning Pipeline Requests ...")    
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("Closing ML Pipeline Server Interface")
            self.channel.close()
            return
            
    # Virtual function, user should override 
    def working_function(self, request_message: bytes) -> bytes:
        return str.encode("TEST")
 

class MLClientInterface:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel: Channel = self.connection.channel()
        
        # create a temporary queue to manage client
        frame: FrameMethod = self.channel.queue_declare(queue='', exclusive = True)
        self.callback_queue = frame.method.queue
        self.channel.basic_consume(
            queue = self.callback_queue, on_message_callback = self.on_response,
            auto_ack = True)

        self.response: bytes = None
        self.correlation_id = None

    def on_response(self, channel: Channel, method: DeliveryProperties,
                    properties: BasicProperties, message_body: bytes):
        if self.correlation_id == properties.correlation_id:
            self.response = message_body
        
    def call(self, message: bytes) -> bytes:
        self.response = None
        # generates a random uid
        self.correlation_id = uuid.uuid4()
        self.channel.basic_publish(exchange='', routing_key = ML_REQUEST_QUEUE_NAME,
                                   properties=pika.BasicProperties(
                                       reply_to = self.callback_queue,
                                       correlation_id = self.correlation_id),
                                   body = message)
        while self.response is None:
            self.connection.process_data_events(time_limit = 30.0 * 60.0)
        return self.response