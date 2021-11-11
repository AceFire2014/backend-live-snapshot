#!/usr/bin/env bash

set -e -u

script_path="$(dirname $0)"
script_name="$(basename $0)"
echo "Running $script_name steps ..."

INVENTORY=nonprod
if [ "x$K8S_NS" == "xprod" ]; then
    INVENTORY=prod
fi
echo "INVENTORY: $INVENTORY"

pushd $ANSIBLE_FOLDER
ansible-playbook -i envs/${INVENTORY} health.yaml -vvvv
popd
