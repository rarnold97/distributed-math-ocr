"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0bimage.proto\x12\x17equation_image_to_latex"\xa3\x01\n\x05Image\x12\x10\n\x08filepath\x18\x01 \x01(\t\x12A\n\x0cequationType\x18\x02 \x01(\x0e2+.equation_image_to_latex.Image.EquationType\x12\n\n\x02id\x18\x03 \x01(\x03"9\n\x0cEquationType\x12\x0b\n\x07DIGITAL\x10\x00\x12\x0f\n\x0bHANDWRITTEN\x10\x01\x12\x0b\n\x07UNKNOWN\x10\x02"<\n\nImageStack\x12.\n\x06images\x18\x01 \x03(\x0b2\x1e.equation_image_to_latex.Imageb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'image_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals['_IMAGE']._serialized_start = 41
    _globals['_IMAGE']._serialized_end = 204
    _globals['_IMAGE_EQUATIONTYPE']._serialized_start = 147
    _globals['_IMAGE_EQUATIONTYPE']._serialized_end = 204
    _globals['_IMAGESTACK']._serialized_start = 206
    _globals['_IMAGESTACK']._serialized_end = 266