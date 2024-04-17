from __future__ import annotations

from typing import TypeAlias
import multiprocessing
from pathlib import Path

from PIL import Image
import pix2tex
from pix2tex.cli import LatexOCR
import pika
from pika.channel import Channel
from pika.spec import BasicProperties
from pika.spec import Basic
from munch import Munch

from mathclips.services import LOCAL_MODE
from mathclips.services.logger import logger
from mathclips.services.mongodb import (MathSymbolImageDatabase, MathSymbolResultDatabase, MLCheckpointDatabase)
from mathclips.services.rmq import get_rmq_connection_parameters
from mathclips.services import IngestQueueNames
from mathclips.proto.pb_py_classes.image_pb2 import Image as ImageProto
from mathclips.proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes
from mathclips.proto.pb_py_classes.ocr_result_pb2 import OCR_Result

DeliveryProperties: TypeAlias = Basic.Deliver
# flip to true when debugging during development
pix2tex_root = Path(pix2tex.__path__[0]).resolve()

class MLPipelineInterface:
    """
    Making this a class in case we need to re-spawn the LatexOCR with updated weights

    Mongo client Interfaces can be shared across class instances, and only need to be loaded once.
    """

    # let the ctor handle the client setup for us
    image_db = MathSymbolImageDatabase()
    result_db = MathSymbolResultDatabase(image_db.db)
    checkpoint_db = MLCheckpointDatabase(image_db.db)

    # this name is important to config settings other than the weights filename, so we omitt the extension
    # until the extension is needed.
    mathclips_weights_name = "mathclips_weights"
    mathclips_config_path = pix2tex_root / "model" / "settings" / "mathclips_final_config.yaml"
    mathclips_resizer_path = pix2tex_root / "model" / "mathclips_checkpoints" / "mathclips_image_resizer.pth"

    @staticmethod
    def get_current_weights_path() -> Path:
        package_checkpoints_dir = pix2tex_root.joinpath("model").joinpath("checkpoints")
        mathclips_checkpoints_dir = pix2tex_root.joinpath("model").joinpath("mathclips_checkpoints")
        mathclips_weights_path = mathclips_checkpoints_dir.joinpath(f"{MLPipelineInterface.mathclips_weights_name}.pth")
        # TODO - Determine how to get new updated weights dimensions to work with model properly
        return mathclips_weights_path if mathclips_weights_path.exists() \
            else package_checkpoints_dir.joinpath("weights.pth")

    @staticmethod
    def get_current_config_path() -> Path:
        if MLPipelineInterface.mathclips_config_path.exists():
            return MLPipelineInterface.mathclips_config_path
        config_dir = pix2tex_root.joinpath("model").joinpath("settings")
        return config_dir.joinpath("config.yaml")

    def __init__(self):
        """
        Upon Initializing this interface, the model will reload the weights file.
        After a training pipeline, the weights will change, so constructing a new interface
        will automatically load the latest model weights for you.
        """

        #modifying the config args from the original library
        # we cannot proceed if we were unable to successfully export resizer weights.
        # the model will not update the resizer weights if accuracy was not improved.

        current_checkpoint_path = MLPipelineInterface.get_current_weights_path()
        ocr_arguments: Munch = None
        if MLPipelineInterface.mathclips_resizer_path.exists():
            ocr_arguments = Munch({'config': str(MLPipelineInterface.mathclips_config_path),
                                'checkpoint': str(current_checkpoint_path),
                                'no_cuda': True, 'no_resize': False})

        self.ocr_model = LatexOCR(arguments = ocr_arguments)
        # open a connection to the ingest queue
        self.rmq_connection: pika.connection.Connection = None
        self.rmq_channel: pika.channel.Channel = None

    def latex_from_image(self, image_msg: ImageProto) -> str:
        image_data: Image = MLPipelineInterface.image_db.get_image(image_msg.uid)
        if image_data is None:
            logger.warning(f"Image does not exist in database: {image_msg.equation_name}")
            return ""
        latex_str: str | None = self._extract_equation_from_image(image_data)
        if latex_str is None:
            error_message: str = f"Could not generate an equation from: {image_data.info['filename']}"
            logger.error(error_message)
            raise RuntimeError(error_message)
        return latex_str
    
    def _extract_equation_from_image(self, image_data: Image) -> str:
        """
        Generate a latex formatted string that uses OCR
        to extract an equation from an input image.
        NOTE: we want to allow the program to exit gracefully,
        so rather than throwing an exception, we will throw None,
        to allow the system to reset or respond to a failure of loading
        an image.  Returning None will indicate this.  Will
        Log if

        Parameters
        ----------
        image_path : a valid image path that contains an equation

        Returns
        -------
        str | None
            latex formatted equation string.
            Returns None if the image cannot be successfully loaded.
        """
        return self.ocr_model(image_data)

    def __enter__(self) -> MLPipelineInterface:
        self.rmq_connection = pika.BlockingConnection(
            get_rmq_connection_parameters(LOCAL_MODE))
        self.rmq_channel = self.rmq_connection.channel()
        self.rmq_channel.queue_declare(queue = IngestQueueNames.RESULT_QUEUE, durable = True)
        return self

    def __exit__(self, execute_type, execute_value, execute_traceback):
        self.rmq_connection.close()

    def send_result_to_ingest_service(self, result: OCR_Result):
        if self.rmq_channel is not None:
            self.rmq_channel.basic_publish(
                exchange='',
                routing_key = IngestQueueNames.RESULT_QUEUE,
                properties = pika.BasicProperties(delivery_mode = pika.DeliveryMode.Persistent),
                body = result.SerializeToString())
            print(f"Sent ML OCR result to ingest queue. Message contents:\n{result}")
        else:
            logger.warning("Cannot Establish RabbitMQ connection to Ingest Service(s)!")

def ml_worker():

    def ml_pipeline_callback(channel: Channel, method: DeliveryProperties,
                             properties: BasicProperties, body: bytes):

        ml_pipeline_interface = MLPipelineInterface()
        # we are assuming that the image class is stored in its own database, and accessible via its uid property
        image_message = ImageProto.FromString(body)
        print(f"Running ML Pipeline for: {image_message.equation_name}. MESSAGE:\n{image_message}")
        latex_equation: str = ml_pipeline_interface.latex_from_image(image_message)
        if latex_equation:
            # TODO - allow more user intervention to determine correctness.
            equation_correct: bool = True
            result_id: UintPackedBytes = ml_pipeline_interface.result_db.store_result(
                latex_result = latex_equation, input_id = image_message.uid, correct = equation_correct)
            result_message = OCR_Result(uid = result_id, latex = latex_equation, input_image_data = image_message)

            # employing a with context to ensure connection is closed
            with ml_pipeline_interface:
                # send to the ingest queue to be displayed to the front end
                ml_pipeline_interface.send_result_to_ingest_service(result_message)
        else:
            logger.warning(f"Was unable to generate a latex equaion for: {image_message.equation_name}")

        channel.basic_ack(delivery_tag = method.delivery_tag)
    connection = pika.BlockingConnection(
        get_rmq_connection_parameters(LOCAL_MODE))
    channel = connection.channel()
    channel.queue_declare(queue = IngestQueueNames.ML_PIPELINE_QUEUE, durable = True)
    print(" [*] Waiting for Messages, CTRL+C to quit.")

    channel.basic_qos(prefetch_count = 1)
    channel.basic_consume(queue = IngestQueueNames.ML_PIPELINE_QUEUE,
                          on_message_callback = ml_pipeline_callback)
    channel.start_consuming()


def ml_worker_factory() -> multiprocessing.Process:
    worker_process = multiprocessing.Process(target = ml_worker, name = "ml_pipeline_worker")
    worker_process.start()
    return worker_process

def main():
    from mathclips.services import NUM_ML_PIPELINES
    processes = [ml_worker_factory() for _ in range(NUM_ML_PIPELINES)]
    for process in processes:
        process.join()

if __name__ == "__main__":
    main()
