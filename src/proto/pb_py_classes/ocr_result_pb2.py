# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: ocr_result.proto
# Protobuf Python Version: 4.25.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import proto.pb_py_classes.image_pb2 as image__pb2
import proto.pb_py_classes.uint_packed_bytes_pb2 as uint__packed__bytes__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10ocr_result.proto\x12\x17\x65quation_image_to_latex\x1a\x0bimage.proto\x1a\x17uint_packed_bytes.proto\"\x8c\x01\n\nOCR_Result\x12\x35\n\x03uid\x18\x01 \x01(\x0b\x32(.equation_image_to_latex.UintPackedBytes\x12\r\n\x05latex\x18\x02 \x01(\t\x12\x38\n\x10input_image_data\x18\x03 \x01(\x0b\x32\x1e.equation_image_to_latex.Imageb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'ocr_result_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_OCR_RESULT']._serialized_start=84
  _globals['_OCR_RESULT']._serialized_end=224
# @@protoc_insertion_point(module_scope)
