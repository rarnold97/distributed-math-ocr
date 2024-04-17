from pathlib import Path

import numpy as np

from mathclips.proto.pb_py_classes.image_pb2 import Image as ProtoImage
from mathclips.proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes
from mathclips.services.mongodb import MathSymbolImageDatabase
from mathclips.services.image_to_equation_interface import Interface_IPC

root_path = Path(__file__).parent.parent.resolve()

def test_database():
    # this data would be available through an upload service
    sample_image_path: Path = root_path / "data" / "test" / "moment_of_intertia_snippet.png"
    input_db = MathSymbolImageDatabase()
    file_storage_id: UintPackedBytes = input_db.store_image(
        sample_image_path,
        ProtoImage.EquationType.DIGITAL,
        processed = False,
        trained = False)

    sample_message = ProtoImage(uid = file_storage_id,
                                equationType = ProtoImage.EquationType.DIGITAL)
    latex_equation: str = Interface_IPC.latex_from_image(image_msg = sample_message)
    Interface_IPC.store_latex_result_to_db(file_storage_id, latex_equation, correct=True)
    
if __name__ == "__main__":
    test_database()
