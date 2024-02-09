#!/usr/bin/bash

# Get the directory of the currently executing script
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

proto_files=($ROOT_DIR/src/proto/*.proto)
proto_names=()

for file in "${proto_files[@]}"; do
    proto_names+=$(basename "$file")
    proto_names+=" "
done
echo ${proto_names}

protoc --python_out=$ROOT_DIR/src/proto/classes --proto_path=$ROOT_DIR/src/proto ${proto_names[@]}
protol --create-package --in-place --python-out $ROOT_DIR/src/proto/classes \
    protoc --proto-path=$ROOT_DIR/src/proto ${proto_names[@]}
