import image_pb2 as _image_pb2
import uint_packed_bytes_pb2 as _uint_packed_bytes_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class OCR_Result(_message.Message):
    __slots__ = ("uid", "latex", "input_image_data")
    UID_FIELD_NUMBER: _ClassVar[int]
    LATEX_FIELD_NUMBER: _ClassVar[int]
    INPUT_IMAGE_DATA_FIELD_NUMBER: _ClassVar[int]
    uid: _uint_packed_bytes_pb2.UintPackedBytes
    latex: str
    input_image_data: _image_pb2.Image
    def __init__(self, uid: _Optional[_Union[_uint_packed_bytes_pb2.UintPackedBytes, _Mapping]] = ..., latex: _Optional[str] = ..., input_image_data: _Optional[_Union[_image_pb2.Image, _Mapping]] = ...) -> None: ...
