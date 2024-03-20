import platform
from pathlib import Path
import subprocess
import sys
import os
import importlib.util
from types import ModuleType

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

def bootstrap():
    """
    rather than having a requirements for the requirements/lock,
    We are going to automatically bootstrap the devkit build by installing
    the required building tools for the user in an ms_devkit specific venv.
    """
    venv_dir = ROOT_DIR.joinpath(".mathclips_venv")
    system_name: str = platform.system()
    is_windows: bool = system_name == "Windows"
    exe_ext = ".exe" if is_windows else ""
    python_venv_bin_dir = venv_dir / "Scripts" if is_windows else \
        venv_dir/"bin"
    venv_python_exe = python_venv_bin_dir / f"python{exe_ext}"
    
    if not venv_dir.exists():
        import venv
        print(f"Creating mathclips virtual enironment at: {venv_dir} ...")
        venv.create(venv_dir, with_pip = True)
        subprocess.run([venv_python_exe, "-m", "pip", "install", "--upgrade", "pip"],
                       check=True)
        # install required build dependencies
        pip_install_command = [venv_python_exe, "-m", "pip", "install", "--upgrade"]
        lock_module: ModuleType = load_module_from_python_script(ROOT_DIR.joinpath("lock.py"))
        pip_install_command.extend(lock_module.required_dependencies)
        subprocess.run(pip_install_command, check = True)

    if Path(sys.executable) != venv_python_exe:
        print(f"Using virtual environment at: {venv_dir} ...")
        # NOTE: An explicit flush is required before calling an `os.exec*`
        # function to prevent the output from being lost
        sys.stdout.flush()
        os.execv(venv_python_exe, [venv_python_exe, *sys.orig_argv[1:]])


if __name__ == "__main__":
    bootstrap()
