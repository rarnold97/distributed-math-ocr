import importlib.util
if importlib.util.find_spec('grpc_tools') is None:
    raise RuntimeError('Please Install grpcio pypi package!')

from pathlib import Path
import sys
import subprocess

proto_dir = Path(__file__).parent.resolve()
output_package_name = "pb_py_classes"
proto_package_dir = proto_dir.joinpath(output_package_name)

if __name__ == "__main__":
    proto_file_stubs = [file.name for file in proto_dir.glob("*.proto")]
    gprc_command = [sys.executable, '-m', 'grpc_tools.protoc',
                    f'-I{proto_dir}',
                    f"--proto_path={proto_dir}",
                    f'--python_out={proto_package_dir}',
                    f'--pyi_out={proto_package_dir}'] \
                    + proto_file_stubs
    subprocess.run(gprc_command, check = True,
                   stdout=sys.stdout, stderr=sys.stderr)
