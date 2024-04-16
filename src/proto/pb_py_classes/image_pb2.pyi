import uint_packed_bytes_pb2 as _uint_packed_bytes_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Image(_message.Message):
    __slots__ = ("uid", "equationType", "equation_name", "author", "parent_section")
    class EquationType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        DIGITAL: _ClassVar[Image.EquationType]
        HANDWRITTEN: _ClassVar[Image.EquationType]
        UNKNOWN: _ClassVar[Image.EquationType]
    DIGITAL: Image.EquationType
    HANDWRITTEN: Image.EquationType
    UNKNOWN: Image.EquationType
    UID_FIELD_NUMBER: _ClassVar[int]
    EQUATIONTYPE_FIELD_NUMBER: _ClassVar[int]
    EQUATION_NAME_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    PARENT_SECTION_FIELD_NUMBER: _ClassVar[int]
    uid: _uint_packed_bytes_pb2.UintPackedBytes
    equationType: Image.EquationType
    equation_name: str
    author: str
    parent_section: str
    def __init__(self, uid: _Optional[_Union[_uint_packed_bytes_pb2.UintPackedBytes, _Mapping]] = ..., equationType: _Optional[_Union[Image.EquationType, str]] = ..., equation_name: _Optional[str] = ..., author: _Optional[str] = ..., parent_section: _Optional[str] = ...) -> None: ...

class ImageStack(_message.Message):
    __slots__ = ("images",)
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    images: _containers.RepeatedCompositeFieldContainer[Image]
    def __init__(self, images: _Optional[_Iterable[_Union[Image, _Mapping]]] = ...) -> None: ...
