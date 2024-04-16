from pathlib import Path

from PIL import Image
from pix2tex.cli import LatexOCR


def test_latex_ocr_install():
    test_image_path = Path(__file__).parent.parent.resolve() / "data" / "test" / "moment_of_intertia_snippet.png"
    pil_image = Image.open(test_image_path)
    model = LatexOCR()
    latex = model(pil_image)
    print(f"Latex Equation Prediction: {latex}")

if __name__ == "__main__":
    test_latex_ocr_install()
