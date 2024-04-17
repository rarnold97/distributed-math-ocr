import uint_packed_bytes_pb2 as _uint_packed_bytes_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TrainRequest(_message.Message):
    __slots__ = ("result_uid", "latex_str")
    RESULT_UID_FIELD_NUMBER: _ClassVar[int]
    LATEX_STR_FIELD_NUMBER: _ClassVar[int]
    result_uid: _uint_packed_bytes_pb2.UintPackedBytes
    latex_str: str
    def __init__(self, result_uid: _Optional[_Union[_uint_packed_bytes_pb2.UintPackedBytes, _Mapping]] = ..., latex_str: _Optional[str] = ...) -> None: ...
