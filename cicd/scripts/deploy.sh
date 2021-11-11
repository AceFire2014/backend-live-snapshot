#!/usr/bin/env bash

set -e -u

script_path="$(dirname $0)"
script_name="$(basename $0)"
echo "Running $script_name steps ..."

source $script_path/envars.sh

INVENTORY=nonprod
if [ "x$K8S_NS" == "xprod" ]; then
    INVENTORY=prod
fi
echo "INVENTORY: $INVENTORY"

echo "+++ printenv +++"
printenv

pushd $ANSIBLE_FOLDER
ansible-playbook -i envs/${INVENTORY} play.yaml -vvvv
popd


