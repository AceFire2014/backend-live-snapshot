#!/usr/bin/env bash

set -e -u

MAIN_IMAGE_TAG="${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}"
NGINX_IMAGE_TAG="nginx:1.19.0-alpine"
