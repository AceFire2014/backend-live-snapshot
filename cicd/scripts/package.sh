#!/usr/bin/env bash

set -e -u

script_path="$(dirname $0)"
script_name="$(basename $0)"
echo "Running $script_name steps ..."

source $script_path/envars.sh

cp $MAIN_IMAGE_FOLDER/.dockerignore .
cp $MAIN_IMAGE_FOLDER/Dockerfile .

docker build \
  -t ${MAIN_IMAGE_TAG} \
  -f Dockerfile .

docker push ${MAIN_IMAGE_TAG}
