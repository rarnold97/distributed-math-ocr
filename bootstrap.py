from pathlib import Path
import sys, os
import importlib.util
from types import ModuleType
import subprocess
import platform
import argparse

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

def bootstrap(is_docker: bool = False):
    venv_dir = ROOT_DIR.joinpath(".venv")
    system_name: str = platform.system()
    is_windows: bool = system_name == "Windows"
    exe_ext = ".exe" if is_windows else ""
    python_venv_bin_dir = venv_dir / "Scripts" if is_windows else \
        venv_dir/"bin"
    python_exe = python_venv_bin_dir / f"python{exe_ext}" if not is_docker else sys.executable
    
    if not venv_dir.exists():
        if not is_docker:
            import venv
            print(f"Creating mathclips virtual enironment at: {venv_dir} ...")
            venv.create(venv_dir, with_pip = True)
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"],
                        check=True)
        # install required build dependencies
        pip_install_command = [python_exe, "-m", "pip", "install", "--upgrade"]
        lock_module: ModuleType = load_module_from_python_script(ROOT_DIR.joinpath("lock.py"))
        pip_install_command.extend(lock_module.required_dependencies)
        subprocess.run(pip_install_command, check = True, stdout = sys.stdout, stderr = sys.stderr)
        subprocess.run([python_exe, "-m", "pip", "install"] + list(lock_module.build_dependencies),
                    check = True, stdout = sys.stdout, stderr = sys.stderr)

        if not is_docker:
            os.execv(python_exe, [python_exe, *sys.orig_argv[1:]])
        
    subprocess.run([sys.executable, '-m', 'pix2tex.model.checkpoints.get_latest_checkpoint'],
                    check = True, stdout = sys.stdout, stderr = sys.stderr)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap script for developing mathclips project.")
    parser.add_argument("--docker-mode", action="store_true", help="install to global pip environment in docker image.")
    command_line_arguments: argparse.Namespace = parser.parse_args()

    bootstrap(command_line_arguments.docker_mode)
