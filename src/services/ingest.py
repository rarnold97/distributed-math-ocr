from typing import Dict, TypeAlias, List
from pathlib import Path
from dataclasses import dataclass, field
import random
import multiprocessing
from itertools import chain
import tempfile
import subprocess
import sys
from datetime import datetime
import shutil

import pika.connection
import pymongo.results
import yaml
import pika
from pika.channel import Channel
from pika.spec import BasicProperties
from pika.spec import Basic
import pix2tex
import pymongo
from PIL import Image
from munch import Munch
DeliveryProperties: TypeAlias = Basic.Deliver

from services import (MIN_TRAIN_BATCH_SIZE, NUM_TRAIN_WORKERS,
                      NUM_RESULT_WORKERS, IngestQueueNames)
from services.logger import logger
from services.rmq import get_rmq_connection_parameters
from services.util import (object_id_from_packed, packed_from_object_id,
                           find_newest_file, update_nested_dict)
from services.mongodb import (MathSymbolImageDatabase, MLCheckpointDatabase,
                              MathSymbolResultDatabase, MathEquationResultRecord)
from services.image_to_equation_interface import MLPipelineInterface
from proto.pb_py_classes.ocr_result_pb2 import OCR_Result
from proto.pb_py_classes.train_pb2 import TrainRequest
from proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes as UintPacked

root_path = Path(__file__).parent.parent.resolve()
pix2tex_root = Path(pix2tex.__path__[0]).resolve()

#cache database clients
image_db = MathSymbolImageDatabase()
result_db = MathSymbolResultDatabase(db = image_db.db)
ml_checkpoints_db = MLCheckpointDatabase(db = image_db.db)
rmq_connection: pika.connection.Connection = pika.BlockingConnection(get_rmq_connection_parameters())

default_result_config_filename = "default_session_equation_sections.yml"

@dataclass
class ImageFileIdAndLabel:
    file_id: UintPacked
    latex_label: str

@dataclass
class SessionResultConfig:
    config_path: Path = root_path / "front_end" / "pages" /  default_result_config_filename
    config_data: Dict = field(default_factory = dict)

# TODO - in future iterations this can be either expanded for authenticated sessions, or replaced with a database.
SESSION_RESULT_CONFIG_MAP = {
    "default": SessionResultConfig()
}

def update_result_config(new_data: dict, session_key: str = "default"):
    result_config = SESSION_RESULT_CONFIG_MAP[session_key]
    if not result_config.config_data:
        with open(result_config.config_path, 'r') as config_file:
            result_config.config_data = yaml.safe_load(config_file)

    # merge the two dictionaries
    update_nested_dict(result_config.config_data, new_data)
    with open(result_config.config_path, 'w') as config_file:
        yaml.safe_dump(result_config.config_data, config_file)

def equation_result_callback(channel: Channel, method: DeliveryProperties,
                            properties: BasicProperties, body: bytes):

    print("Adding ML Pipeline result to database!")
    result_message = OCR_Result.FromString(body)
    config_data = {
        result_message.input_image_data.parent_section: {
            result_message.input_image_data.equation_name: dict(
                author = result_message.input_image_data.author,
                latex = result_message.latex,
                db_id = dict(first_bits = result_message.uid.first_bits,
                               last_bits = result_message.uid.last_bits))
            }
        }
    update_result_config(config_data)
    # TODO - figure out a better way to validate correctness
    record_id: UintPacked = result_db.store_result(
        result_message.latex, result_message.input_image_data.uid,
        correct = True)
    if record_id is not None:
        logger.info("Successfully added ML Pipeline Result to Database!")
        logger.info("Result Record: ", object_id_from_packed(record_id))
        channel.basic_ack(delivery_tag = method.delivery_tag)

def equation_result_listener():
    channel: Channel = rmq_connection.channel()
    channel.queue_declare(queue = IngestQueueNames.RESULT_QUEUE, durable = True)
    print(" [*] Waiting for result messages. CTRL+C to quit.")
    channel.basic_qos(prefetch_count = 1)
    channel.basic_consume(queue = IngestQueueNames.RESULT_QUEUE,
                          on_message_callback = equation_result_callback)
    channel.start_consuming()

def equation_result_worker_factory() -> multiprocessing.Process:
    worker_process = multiprocessing.Process(target = equation_result_listener, name = "equation_result_worker")
    worker_process.start()
    return worker_process

@dataclass
class TrainingBatch:
    train_image_file_ids: List[UintPacked] = field(default_factory = list)
    train_latex_labels: List[str] = field(default_factory = list)
    val_image_file_ids: List[UintPacked] = field(default_factory = list)
    val_latex_labels: List[str] = field(default_factory = list)

def train_worker(batch: TrainingBatch,
                 image_db: MathSymbolImageDatabase, checkpoint_db: MLCheckpointDatabase):

    # create a temp dir to load image data from database and create a temporary dataset, then cleanup from disk
    # the temp dir will automatically clean itself up, in case of any critical failures that will inevitably occur.
    # failure to clean this up would monopolize server disk space behind the scenes
    model_dir = pix2tex_root.joinpath("model")
    package_checkpoints_dir = model_dir.joinpath("checkpoints")
    checkpoints_dir = model_dir.joinpath("mathclips_checkpoints")
    checkpoints_dir.mkdir(exist_ok = True, parents = True)

    mathclips_weight_path = checkpoints_dir.joinpath(f"{MLPipelineInterface.mathclips_weights_name}.pth")
    current_checkpoint_path = mathclips_weight_path if mathclips_weight_path.exists() else None

    mathclips_resizer_path = MLPipelineInterface.mathclips_resizer_path
    # the model interface expects the explicit name 'image_resizer', we cannot override it with a custom name
    # therefore, we will copy the appropriate resizer to
    resizer_path = checkpoints_dir.joinpath("image_resizer.pth")
    if not resizer_path.exists():
        seed_resizer_path = mathclips_resizer_path if mathclips_resizer_path.exists() else \
            package_checkpoints_dir.joinpath("image_resizer.pth")

        shutil.copy2(seed_resizer_path, checkpoints_dir.joinpath("image_resizer.pth"))

    with tempfile.TemporaryDirectory() as temp_dir:
        # copy all input datafiles here
        temp_dir_path = Path(temp_dir)
        train_dir = temp_dir_path.joinpath("train")
        train_dir.mkdir(parents = True, exist_ok = True)
        val_dir = temp_dir_path.joinpath("val")
        val_dir.mkdir(parents = True, exist_ok = True)

        def save_temp_image(fid: UintPacked, out_dir: Path, index: int):
            pil_image: Image = image_db.get_image(fid)
            orig_ext: str = Path(pil_image.info["filename"]).suffix
            basename: str = "{:07d}".format(index)
            temp_path = out_dir.joinpath(basename).with_suffix(orig_ext)
            pil_image.save(str(temp_path))

        def save_labels(out_dir: Path, labels: List[str], filename: str):
            label_file_contents = '\n'.join(labels)
            label_file_path = out_dir.joinpath(filename)
            with open(label_file_path, 'w') as label_file:
                label_file.write(label_file_contents)
            return label_file_path

        for i, fid in enumerate(batch.train_image_file_ids):
            save_temp_image(fid, train_dir, i)
        train_labels_path: Path = \
            save_labels(train_dir, batch.train_latex_labels, "mathclips_train_labels.txt")

        for i, fid in enumerate(batch.val_image_file_ids):
            save_temp_image(fid, val_dir, i)
        val_labels_path: Path = \
            save_labels(val_dir, batch.val_latex_labels, "mathclips_val_labels.txt")

        torch_train_dataset_path: Path = temp_dir_path.joinpath("mathclips_train_dataset.pkl")
        subprocess.run([sys.executable, "-m", "pix2tex.dataset.dataset", "--equations", train_labels_path,
                        "--images", train_dir, "--out", torch_train_dataset_path],
                       check = True, stderr = sys.stderr, stdout = sys.stdout)

        torch_val_dataset_path: Path = temp_dir_path.joinpath("mathclips_val_dataset.pkl")
        subprocess.run([sys.executable, "-m", "pix2tex.dataset.dataset", "--equations", val_labels_path,
                        "--images", val_dir, "--out", torch_val_dataset_path],
                       check = True, stderr = sys.stderr, stdout = sys.stdout)

        # load in the default config, and replace settings where appropriate
        # using the original hyperparameters the author designed
        with open(model_dir / "settings" / "config.yaml", 'r') as config_template_file:
            train_config_template = Munch(yaml.safe_load(config_template_file))

        # override the default settings
        current_batch_size: int = min(64,
                                  min(len(batch.val_image_file_ids), len(batch.train_image_file_ids)))
        val_batch_size: int = min(64, len(batch.val_latex_labels))
        train_config_template.name = MLPipelineInterface.mathclips_weights_name
        train_config_template.batchsize = current_batch_size
        train_config_template.data = str(torch_train_dataset_path)
        train_config_template.valdata = str(torch_val_dataset_path)
        train_config_template.valbatches = val_batch_size
        train_config_template.model_path = str(checkpoints_dir)
        if current_checkpoint_path:
            train_config_template.load_chkpt = str(current_checkpoint_path)
        train_config_template.max_width = 512
        #train_config_template.max_width = 1024
        train_config_template.max_height = 512
        train_config_template.debug = True
        #train_config_template.encoder_structure = 'vit'
        train_config_template.encoder_structure = 'hybrid'
        train_config_template.pad = True

        train_config_path = model_dir.joinpath("mathclips_config.yml")
        with open(train_config_path, 'w') as train_config:
            yaml.safe_dump(dict(train_config_template), train_config)

        subprocess.run([sys.executable, "-m", "pix2tex.train", "--config", train_config_path, "--debug"],
                       check = True, stderr = sys.stderr, stdout = sys.stdout)

        # the train module outputs new weights and configs to: config.model_path / config.name
        batch_run_output_dir = checkpoints_dir.joinpath(MLPipelineInterface.mathclips_weights_name)
        newest_checkpoint_path = find_newest_file(batch_run_output_dir, filter_pattern = '*.pth')
        # the filename stored in the database will have extra info associated with it related to the training run.
        # the production file will just be called mathclips_weights.pth to simplify the system
        # the database will store more of the metadata that give better detail about how the weights file was constructed.
        checkpoint_db.store_checkpoint_file(checkpoint_path = newest_checkpoint_path,
                                            timestamp = datetime.now(),
                                            train_file_ids = batch.train_image_file_ids)

        new_config_path = batch_run_output_dir.joinpath("config.yaml")
        if new_config_path.exists():
            shutil.copy2(new_config_path, MLPipelineInterface.mathclips_config_path)
        shutil.copy2(newest_checkpoint_path, mathclips_weight_path)

        subprocess.run([sys.executable, "-m", "pix2tex.train_resizer",
                        "--config", MLPipelineInterface.mathclips_config_path,
                        "--out", mathclips_resizer_path],
                       stderr = sys.stderr, stdout = sys.stdout, check = True)

        if mathclips_resizer_path.exists():
            shutil.copy2(mathclips_resizer_path, resizer_path)
        shutil.rmtree(batch_run_output_dir, ignore_errors = True)
        train_config_path.unlink(missing_ok = True)
        logger.info(f"Updated OCR Model weights at: {mathclips_weight_path}")

def train_callback(channel: Channel, method: DeliveryProperties,
                   properties: BasicProperties, body: bytes):

        train_request = TrainRequest.FromString(body)
        result_record: MathEquationResultRecord = result_db.find_one(
            dict(_id = object_id_from_packed(train_request.result_uid)))
        if result_record is None:
            logger.warning(f"Could not find result record with id message: {train_request.result_uid}")
            channel.basic_ack(delivery_tag = method.delivery_tag)
            return
        # designate a record for training
        image_db.collection.update_one(
            dict(_id = result_record["input_entry_id"]),
            {'$set': dict(train_label = train_request.latex_str, needs_train = True)},
            upsert = False)

        # we want enough data for train data + validation data
        # going to use 20% of train batch size, or half the size
        validation_size = max(1, max(int(0.2*float(MIN_TRAIN_BATCH_SIZE)), int(MIN_TRAIN_BATCH_SIZE / 2)))
        # in developer mode, this will require 3 images, with a MIN_TRAIN_BATCH_SIZE of 2
        train_threshold: int = MIN_TRAIN_BATCH_SIZE + validation_size
        num_matches: int = image_db.collection.count_documents(dict(needs_train = True))
        if num_matches >= train_threshold:
            print("Kicking off a training batch run!")
            records_marked_train_cursor: pymongo.CursorType = image_db.query(dict(needs_train = True))
            # delegate to a function that will kick off a training run
            # probably need a worker queue here
            query_batch = [ImageFileIdAndLabel(file_id = packed_from_object_id(post['file_storage_id']), \
                                        latex_label = post['train_label']) for post in records_marked_train_cursor]
            validation_sample_indexes = random.sample(range(num_matches), validation_size)
            train_batch = TrainingBatch()
            for i, id_and_label in enumerate(query_batch):
                if i in validation_sample_indexes:
                    train_batch.val_image_file_ids.append(id_and_label.file_id)
                    train_batch.val_latex_labels.append(id_and_label.latex_label)
                    # shorten the list to make search nlog(n)
                    validation_sample_indexes.remove(i)
                else:
                    train_batch.train_image_file_ids.append(id_and_label.file_id)
                    train_batch.train_latex_labels.append(id_and_label.latex_label)

            assert len(train_batch.val_latex_labels) > 0
            # kick off a training worker
            print(f"Training using: {len(train_batch.train_latex_labels)} ",
                  f"TRAIN SAMPLES and {len(train_batch.val_latex_labels)} VALIDATION SAMPLES!")
            train_worker(
                batch = train_batch, image_db = image_db, checkpoint_db = ml_checkpoints_db)

            # upon successful training batch run, set needs train back to false
            many_result: pymongo.results.UpdateResult = \
                image_db.collection.update_many(
                    filter = dict(needs_train = True),
                    update = {'$set': {'needs_train': False}})
            assert many_result is not None and many_result.modified_count == len(query_batch)
            print("Successfully Unmarked Samples for Training!")

        channel.basic_ack(delivery_tag = method.delivery_tag)

def train_message_listener():
    channel: Channel = rmq_connection.channel()
    channel.queue_declare(queue = IngestQueueNames.TRAIN_QUEUE, durable = True)
    print(" [*] Waiting for train request messages. CTRL+C to exit.")
    channel.basic_qos(prefetch_count = 1)
    channel.basic_consume(queue = IngestQueueNames.TRAIN_QUEUE,
                          on_message_callback = train_callback)
    channel.start_consuming()

def train_message_worker_factory() -> multiprocessing.Process:
    worker_process = multiprocessing.Process(target = train_message_listener, name = "train_message_worker")
    worker_process.start()
    return worker_process

def test_train_queue_plumbing():
    """
    Use this function that uses test images in the database to test code plumbing.
    Depending on the state of your mongo DB, you may need to alter the image ids
    provided in this test function.
    """
    from bson import ObjectId

    train_batch = TrainingBatch(
        train_image_file_ids = [
            packed_from_object_id(ObjectId("661df3dc484463d220beaf21")),
            packed_from_object_id(ObjectId("661df41c484463d220beaf27"))],
        train_latex_labels = [
            "L = L_1e_1 + L_2e_2 + L_3e_3 = \Sum_{i = 1}^{3}I_iw_ie_i",
            "z = \\frac{x - \\mu}{\\sigma}"],
        val_image_file_ids = [packed_from_object_id(ObjectId("661df5013c06a79211fcfdc4")),],
        val_latex_labels = ["R = \\left( 1 + \\frac{\\Alpha\\Theta}{N} \\right)^{N} \\approx e^{\\Alpha\\Theta}",]
    )

    train_worker(train_batch, image_db, ml_checkpoints_db)
    # test to make sure the new weights can actually be loaded in the ctor
    ml_interface = MLPipelineInterface()



def main():
    train_message_workers = [train_message_worker_factory() for _ in range(NUM_TRAIN_WORKERS)]
    result_message_workers = [equation_result_worker_factory() for _ in range(NUM_RESULT_WORKERS)]

    for worker in chain(train_message_workers, result_message_workers):
        worker.join()

if __name__ == "__main__":
    main()
    #equation_result_listener()
    #train_message_listener()
    #test_train_queue_plumbing()
