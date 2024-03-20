from pathlib import Path

from PIL import Image
from pix2tex.cli import LatexOCR

from ocr_services.logger import logger
from proto.classes import image_pb2 as ImageProto


def _extract_equation_from_image(image_path: Path) -> str | None:
    """
    Generate a latex formatted string that uses OCR
    to extract an equation from an input image.
    NOTE: we want to allow the program to exit gracefully,
    so rather than throwing an exception, we will throw None,
    to allow the system to reset or respond to a failure of loading
    an image.  Returning None will indicate this.  Will
    Log if

    Parameters
    ----------
    image_path : a valid image path that contains an equation

    Returns
    -------
    str | None
        latex formatted equation string.
        Returns None if the image cannot be successfully loaded.
    """
    if not image_path.exists():
        return None

    image = Image.open(image_path)
    computer_vision_model = LatexOCR()
    return computer_vision_model(image)


class Interface_IPC:

    @staticmethod
    def latex_from_image(image_msg: ImageProto)->str:
        latex_str: str | None = _extract_equation_from_image(image_msg.filepath)
        if latex_str is None:
            err_msg: str = f"Could not generate an equation from: {image_msg.filepath}"
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        return latex_str
