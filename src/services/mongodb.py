from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from pprint import pprint
from datetime import datetime
from typing import List, Any
import enum

from bson.objectid import ObjectId
from pymongo import MongoClient

mongo_port = os.environ.get('MONGO_PORT', int(27017))
mongo_url = f"mongodb://localhost:{mongo_port}/"


def dict_to_intersection_query(dictionary: dict, uid: int|bytes|None = None) -> dict:
    query_list = [{key: value} for key, value in dictionary.items() if value is not None]
    if uid is not None:
        id_bytes = uid
        if isinstance(uid, int):
            id_bytes = uid.to_bytes(length=12)
        query_list.insert(0, {"_id", ObjectId(id_bytes)})
    return {"$and": query_list}

class MathclipsDatabase:
    # going to connect to the standard default mongo client
    client = MongoClient(mongo_url,
                         username="ryanm",
                         password="1997")
    db = client["mathclips_data"]

    def __init__(self, collection_name: str):

        # initialize the two primary database collections
        self.collection = self.db[collection_name]

    def record_from_id(self, uid: int):
        return self.collection.find_one({"_id": ObjectId(uid.to_bytes(length = 12))})

    def delete(self, uid: int):
        self.collection.delete_one({"_id": ObjectId(uid.to_bytes(length = 12))})

    def get_all_record_object_ids(self):
        cursor = self.collection.find({})
        return [doc['_id'] for doc in cursor]

    def query(self, query: dict):
        return self.collection.find(query)

    def insert_single_record(self, record: MathSymbolImageRecord | MLCheckpointRecord):
        post_id: ObjectId = self.collection.insert_one(asdict(record))
        assert post_id.is_valid()
    
    def insert_many_records(self, records: List[MathSymbolImageRecord | MLCheckpointRecord]):
        insert_result = self.collection.insert_many([asdict(record) for record in records])
        assert insert_result

class EquationOriginationType(enum.IntEnum):
    DIGITAL = 0
    HANDWRITTEN = 1
    
@dataclass
class MathSymbolImageRecord:
    image_filename: str|None = None
    processed: bool|None = None
    trained: bool|None = None
    is_correct: bool|None = None
    equation_type: EquationOriginationType|None = None
    latex_label: str|None = None
    
    def as_intersection_query_filter(self, uid: int|bytes|None = None)->dict:
        return dict_to_intersection_query(asdict(self), uid)

class MathSymbolImageDatabase(MathclipsDatabase):
    
    def __init__(self):
        super().__init__("math_symbol_image_data")
    
    def intersection_query(self, uid: int|None = None, image_filename: str|None = None,
                    processed: bool|None = None, trained: bool|None = None,
                    is_correct: bool|None = None,
                    equation_type: EquationOriginationType|None = None,
                    latex_label: str|None = None) -> dict:
        record = MathSymbolImageRecord(
            image_filename=image_filename, processed = processed,
            trained = trained, is_correct = is_correct,
            equation_type = equation_type, latex_label = latex_label)
        return self.collection.find(record.as_intersection_query_filter(uid))
    
@dataclass
class MLCheckpointRecord:
    checkpoint_filename: str|None = None
    date_created: datetime|None = None
    training_file_ids: List[int]|None = None
    
    def as_intersection_query_filter(self, uid: int|bytes|None = None) -> dict:
        return dict_to_intersection_query(asdict(self), uid)
    
class MLCheckpointDatabase(MathclipsDatabase):
    
    def __init__(self):
        super().__init__("ml_checkpoint_data")

    def intersection_query(self, uid: int|None = None,
                           checkpoint_filename: str|None = None,
                           date_created: datetime|None = None,
                           training_file_ids: List[int]|None = None) -> dict:

        record = MLCheckpointRecord(
            checkpoint_filename = checkpoint_filename, date_created = date_created,
            training_file_ids = training_file_ids)
        return self.collection.find(record.as_intersection_query_filter(uid))
