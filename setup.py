"""
According to the PEP standard and the setuptools package, setuptools itself is NOT
deprecated.  the distutils package is depreceated, as well as using setup.py as a cli.
`python -m build .` is the preferred method, but the setuptools and setuptools.setup()
build tools are perfectly valid.  It is also valid to have a setup.py script instead of
the more declaritive pyproject.toml.  For the M&S team of DARPA-AIR, it is preferred
to use the language to define the build script, since we do not distribute a pure-python
package and rely on several C++ artifacts to distribute our software.

This script will depend on one PYPI package: setuptools
This is the defacto python build backend. Setuptools
is also compliant with PEP 517.

SOURCES:
-------
explanation of deprecated features: https://packaging.python.org/en/latest/discussions/setup-py-deprecated/
valid setuptools commands: https://setuptools.pypa.io/en/latest/deprecated/changed_keywords.html
setuptools homepage: https://setuptools.pypa.io/en/latest/index.html

build API: https://build.pypa.io/en/stable/api.html#build.ProjectBuilder
"""
from pathlib import Path
import importlib.util
from types import ModuleType
from typing import List

from setuptools import setup, find_packages

ROOT_DIR = Path(__file__).parent.resolve()

def load_module_from_python_script(script_filename: Path) -> ModuleType:
    """
    importing code from a neighboring script
    wanting to get path and metadata from the setup.py config
    https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    https://stackoverflow.com/questions/67631/how-can-i-import-a-module-dynamically-given-the-full-path
    """
    spec = importlib.util.spec_from_file_location(script_filename.stem, script_filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_project_dependencies() -> List[str]:
    """
    We do not want the lock module to persist, just grab the dependency lists
    """
    lock: ModuleType = load_module_from_python_script(ROOT_DIR.joinpath("lock.py"))
    required_dependencies = lock.required_dependencies
    return list(required_dependencies)
    
with open(ROOT_DIR.joinpath(".VERSION"), 'r') as version_file:
    version_str: str = version_file.read()
PROJECT_VERSION: str = version_str.strip()

required_dependencies = load_project_dependencies()

with open(ROOT_DIR.joinpath("README.md"), 'r') as readme_file:
    readme_contents: str = readme_file.read()
    
data_dir = ROOT_DIR.joinpath("data")
sample_images = [str(image_file.relative_to(data_dir)) for image_file in data_dir.glob("**/*.png")]

# source: https://setuptools.pypa.io/en/latest/deprecated/changed_keywords.html
setup(
    name = "mathclips",
    version = PROJECT_VERSION,
    description="Mathmatical Symbol OCR, Distributed Web Application",
    long_description = readme_contents,
    author = "Ryan Arnold",
    author_email = "<arnold.227@wright.edu>",
    packages=find_packages(where=".", exclude=["examples", "extern", "test"]),
    license_files = ["LICENSE.md",],
    keywords = ["wsf_python", "afsim"],
    project_urls = dict(Homepage = "https://github.com/rarnold97/distributed-math-ocr"),
    python_requires = ">=3.10",
    entry_points = dict(console_scripts = ["run_frontend = mathclips.front_end.run_streamlit:main",]),
    install_requires = list(required_dependencies),
    include_package_data = True)
