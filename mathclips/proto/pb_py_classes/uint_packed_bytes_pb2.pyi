from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class UintPackedBytes(_message.Message):
    __slots__ = ("first_bits", "last_bits")
    FIRST_BITS_FIELD_NUMBER: _ClassVar[int]
    LAST_BITS_FIELD_NUMBER: _ClassVar[int]
    first_bits: int
    last_bits: int
    def __init__(self, first_bits: _Optional[int] = ..., last_bits: _Optional[int] = ...) -> None: ...
