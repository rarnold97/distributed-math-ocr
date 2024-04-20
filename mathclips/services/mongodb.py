from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from datetime import datetime
from typing import List, TypeAlias, Tuple, Optional, IO
from pathlib import Path

from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.results import InsertManyResult, InsertOneResult
import gridfs
from PIL import Image

from mathclips.services import MONGO_DOCKER_IP, MONGO_PORT
from mathclips.proto.pb_py_classes.image_pb2 import Image as ProtoImage
from mathclips.proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes
from mathclips.services.util import object_id_from_packed, packed_from_object_id

def dict_to_intersection_query(dictionary: dict, uid: UintPackedBytes|bytes|None = None) -> dict:
    query_list = [{key: value} for key, value in dictionary.items() if value is not None]
    if uid is not None:
        object_id: ObjectId = None
        if isinstance(uid, UintPackedBytes):
            object_id = object_id_from_packed(uid)
        elif isinstance(uid, bytes):
            object_id = ObjectId(uid)
        query_list.insert(0, {"_id", object_id})
    return {"$and": query_list}

@dataclass
class MathSymbolImageRecord:
    image_filename: str|None = None
    file_storage_id: ObjectId|None = None
    image_size: Tuple|None = None
    image_mode: str|None = None
    needs_train: bool|None = False
    train_label: str|None = None
    equation_type: ProtoImage.EquationType|None = None
    equation_name: str|None = None
    equation_section: str|None = None
    author_name: str|None = None
    
    def as_intersection_query_filter(self, uid: UintPackedBytes|bytes|None = None)->dict:
        return dict_to_intersection_query(asdict(self), uid)

@dataclass
class MLCheckpointRecord:
    file_storage_id: ObjectId|None = None
    checkpoint_filename: str|None = None
    date_created: datetime|None = None
    training_file_ids: List[ObjectId]|None = None
    
    def as_intersection_query_filter(self, uid: UintPackedBytes|bytes|None = None) -> dict:
        return dict_to_intersection_query(asdict(self), uid)

@dataclass
class MathEquationResultRecord:
    input_entry_id: ObjectId|None = None
    is_correct: bool|None = None
    latex_label: str|None = None

    def as_intersection_query_filter(self, uid: UintPackedBytes|bytes|None = None) -> dict:
        return dict_to_intersection_query(asdict(self), uid)

RecordType: TypeAlias = MathSymbolImageRecord | MLCheckpointRecord | MathEquationResultRecord

def object_id_query_from_packed(uid: UintPackedBytes) -> ObjectId:
    object_id: ObjectId = object_id_from_packed(uid)
    return dict(_id = object_id)

class MathclipsDatabase:
    # going to connect to the standard default mongo client

    def __init__(self, collection_name: str,
                 db: Optional[MongoClient] = None,
                 file_storage: Optional[gridfs.GridFS] = None):

        if db is None:
            mongo_url = f"mongodb://{MONGO_DOCKER_IP}:{MONGO_PORT}/"
            mongo_client = MongoClient(mongo_url,
                                    username="admin",
                                    password="admin123")
            self.db = mongo_client["mathclips_data"]
        else:
            self.db = db

        self.file_storage = file_storage
        # initialize the two primary database collections
        self.collection = self.db[collection_name]

    def record_from_id(self, uid: UintPackedBytes):
        return self.collection.find_one(object_id_query_from_packed(uid))

    def delete(self, uid: UintPackedBytes):
        self.collection.delete_one(object_id_query_from_packed(uid))

    def get_all_record_object_ids(self):
        cursor = self.collection.find({})
        return [doc['_id'] for doc in cursor]

    def query(self, query: dict):
        return self.collection.find(query)

    def find_one(self, filter: dict):
        return self.collection.find_one(filter)

    def insert_single_record(self, record: RecordType) -> UintPackedBytes:
        post_result: InsertOneResult = self.collection.insert_one(asdict(record))
        assert ObjectId.is_valid(post_result.inserted_id)
        return packed_from_object_id(post_result.inserted_id)
    
    def insert_many_records(self, records: List[RecordType]) -> List[int]:
        insert_results: InsertManyResult = self.collection.insert_many([asdict(record) for record in records])
        assert insert_results
        return [packed_from_object_id(id) for id in insert_results.inserted_ids]


class MathSymbolImageDatabase(MathclipsDatabase):
    
    collection_name: str = "math_symbol_image_data"

    def __init__(self, db: Database = None, file_storage: Optional[gridfs.GridFS] = None):
        super().__init__(db = db, file_storage = file_storage,
                         collection_name = MathSymbolImageDatabase.collection_name)

        if file_storage is None and self.file_storage is None:
            self.file_storage = gridfs.GridFS(self.db, self.collection.name)
    
    def intersection_query(self,
                    uid: UintPackedBytes|bytes|None = None,
                    image_filename: str|None = None,
                    file_storage_id: UintPackedBytes|None = None,
                    image_size: Tuple = None,
                    image_mode: str = None,
                    needs_train: bool|None = False,
                    train_label: str|None = None,
                    equation_type: ProtoImage.EquationType|None = None,
                    equation_name: str|None = None,
                    equation_section: str|None = None,
                    author_name: str|None = None) -> dict:
        record = MathSymbolImageRecord(
            image_filename=image_filename,
            file_storage_id = object_id_from_packed(file_storage_id),
            image_size = image_size,
            image_mode = image_mode,
            needs_train = needs_train,
            train_label = train_label,
            equation_type = equation_type,
            equation_name = equation_name,
            equation_section = equation_section,
            author_name = author_name)
        return self.collection.find(record.as_intersection_query_filter(uid))
    
    def store_image(self, image: Path | IO | Image.Image,
                        image_basename: str,
                        equation_type: ProtoImage.EquationType,
                        needs_train: bool = False,
                        equation_name: str = "",
                        equation_section: str = "",
                        author_name: str = "") -> UintPackedBytes:
        
        file_storage_id: ObjectId
        pillow_image: Image.Image
        if isinstance(image, Image.Image):
            pillow_image = image
        else:
            pillow_image = Image.open(image)
        file_storage_id = self.file_storage.put(pillow_image.tobytes(), filename = image_basename)
        assert ObjectId.is_valid(file_storage_id)
        locals().get('kwargs')
        record = MathSymbolImageRecord(image_filename = image_basename, file_storage_id = file_storage_id,
                                       image_size = pillow_image.size, image_mode = pillow_image.mode,
                                       equation_type = equation_type, needs_train = needs_train,
                                       equation_name = equation_name, equation_section = equation_section,
                                       author_name = author_name)
        record_id = self.insert_single_record(record)
        return packed_from_object_id(file_storage_id)
    
    def get_image(self, file_id: UintPackedBytes) -> Image|None:
        formatted_file_id = object_id_from_packed(file_id)
        image_record = self.collection.find_one(dict(file_storage_id = formatted_file_id),
                                                projection = dict(image_mode = True, image_size = True))
        if image_record is None:
            return None
        image_file_buffer = self.file_storage.get(formatted_file_id)
        image_data = Image.frombytes(image_record["image_mode"], image_record["image_size"],
                                     image_file_buffer.read())
        filename_path = Path(image_file_buffer.filename)
        if not filename_path.suffix:
            image_data.info["filename"] = str(filename_path.with_suffix('.png'))
        else:
            image_data.info["filename"] = str(filename_path)
        return image_data
        
    
class MLCheckpointDatabase(MathclipsDatabase):
    
    collection_name: str = "ml_checkpoint_data"

    def __init__(self, db: Optional[Database] = None, file_storage: Optional[gridfs.GridFS] = None):
        super().__init__(db = db, file_storage = file_storage,
                         collection_name = MLCheckpointDatabase.collection_name)
        if self.file_storage is None and file_storage is None:
            self.file_storage = gridfs.GridFS(self.db, self.collection.name)

    def store_checkpoint_file(self, checkpoint_path: Path, timestamp: datetime,
                              train_file_ids: List[UintPackedBytes]) -> UintPackedBytes:
        checkpoint_binary_data: bytes
        with open(checkpoint_path, 'rb') as file:
            checkpoint_binary_data = file.read()
        file_id: ObjectId = self.file_storage.put(checkpoint_binary_data, filename = checkpoint_path.name)
        assert ObjectId.is_valid(file_id)

        record = MLCheckpointRecord(
            file_storage_id = file_id,
            checkpoint_filename = checkpoint_path.name,
            date_created = timestamp,
            training_file_ids = [object_id_from_packed(packed) for packed in train_file_ids])
        return self.insert_single_record(record)

    def get_checkpoint_binary_data(self, file_id: UintPackedBytes) -> Tuple[bytes, str]:
        formatted_file_id = object_id_from_packed(file_id)
        checkpoint_record: MLCheckpointRecord = self.collection.find_one(dict(file_storage_id = formatted_file_id))
        assert checkpoint_record is not None
        checkpoint_file_buffer = self.file_storage.get(formatted_file_id)
        return checkpoint_file_buffer.read(), checkpoint_record.checkpoint_filename

    def intersection_query(self, uid: UintPackedBytes|None = None,
                           file_storage_id: UintPackedBytes|None = None,
                           checkpoint_filename: str|None = None,
                           date_created: datetime|None = None,
                           training_file_ids: List[UintPackedBytes]|None = None) -> dict:

        record = MLCheckpointRecord(
            file_storage_id = object_id_from_packed(file_storage_id),
            checkpoint_filename = checkpoint_filename, date_created = date_created,
            training_file_ids = [object_id_from_packed(id) for id in training_file_ids])
        return self.collection.find(record.as_intersection_query_filter(uid))


class MathSymbolResultDatabase(MathclipsDatabase):
    
    collection_name: str = "math_equation_result_data"

    def __init__(self, db: Optional[Database] = None):
        super().__init__(db = db, collection_name = MathSymbolResultDatabase.collection_name)
        
    def intersection_query(self, uid: UintPackedBytes|None = None,
                           input_entry_id: UintPackedBytes|None = None,
                           is_correct: bool|None = None,
                           latex_label: str|None = None) -> dict:
        record = MathEquationResultRecord(input_entry_id = object_id_from_packed(input_entry_id),
                                          is_correct = is_correct, latex_label = latex_label)
        return self.collection.find(record.as_intersection_query_filer(uid))
    
    def store_result(self, latex_result: str, input_id: UintPackedBytes, correct: bool) -> UintPackedBytes:
        record = MathEquationResultRecord(input_entry_id = object_id_from_packed(input_id),
                                          is_correct = correct,
                                          latex_label = latex_result)
        return self.insert_single_record(record)
