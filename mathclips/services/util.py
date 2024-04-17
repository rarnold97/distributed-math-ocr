from pathlib import Path
import struct
from typing import Dict

from mathclips.proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes
import bson

PROJECT_ENDIANNESS = '!' # network big-endian
uint32_format = 'I'
uint64_format = 'Q'
ObjectID_len = int(12)

def object_id_from_packed(uid: UintPackedBytes) -> bson.ObjectId:
    pack_format = f"{PROJECT_ENDIANNESS}{uint64_format}{uint32_format}"
    packed_data_buffer: bytes = struct.pack(pack_format, uid.first_bits, uid.last_bits)
    return bson.ObjectId(packed_data_buffer)
    
def packed_from_object_id(oid: bson.ObjectId) -> UintPackedBytes:
    byte_array = oid.binary
    assert len(byte_array) == ObjectID_len
    unpack_32_format = f"{PROJECT_ENDIANNESS}{uint32_format}"
    unpack_64_format = f"{PROJECT_ENDIANNESS}{uint64_format}"
    uint64_tuple, uint32_tuple = struct.unpack(unpack_64_format, byte_array[:8]),\
        struct.unpack(unpack_32_format, byte_array[8:])
    uint64, = uint64_tuple
    uint32, = uint32_tuple
    return UintPackedBytes(first_bits = uint64, last_bits = uint32)

def find_newest_file(root_dir: Path, filter_pattern: str = '*'):
    newest_path: Path = None
    latest_timestamp = None
    for file in root_dir.glob(filter_pattern):
        if file.is_file():
            timestamp = file.stat().st_mtime

            if latest_timestamp is None or timestamp > latest_timestamp:
                newest_path = file
                latest_timestamp = timestamp
    return newest_path

def update_nested_dict(old_dict: Dict, new_dict: Dict):
    """
    This function assumes that we only have one section per layer.
    The leaf node of the dictionary will be a dictionary with metadata, that
    will contain multiple items
    """
    key: str
    new_value: Dict|str
    key, new_value = tuple(new_dict.items())[0]
    if isinstance(new_value, dict) and len(new_value) == 1:
        if key not in old_dict:
            old_dict[key] ={}
        update_nested_dict(old_dict[key], new_value)
    else:
        old_dict[key] = new_value
