#!/bin/sh
docker build . -t zephyr-scripthost
docker run -it -e ZEPHYR_STORAGE_NAME=$(../../deploy/getsetting instance_name) -e ZEPHYR_STORAGE_KEY=$(../../deploy/getsetting storage_key) zephyr-scripthost
