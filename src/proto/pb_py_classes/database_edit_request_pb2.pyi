import uint_packed_bytes_pb2 as _uint_packed_bytes_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EditRequest(_message.Message):
    __slots__ = ("result_db_id", "delete_entry")
    RESULT_DB_ID_FIELD_NUMBER: _ClassVar[int]
    DELETE_ENTRY_FIELD_NUMBER: _ClassVar[int]
    result_db_id: _uint_packed_bytes_pb2.UintPackedBytes
    delete_entry: bool
    def __init__(self, result_db_id: _Optional[_Union[_uint_packed_bytes_pb2.UintPackedBytes, _Mapping]] = ..., delete_entry: bool = ...) -> None: ...
