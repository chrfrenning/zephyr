#!/bin/sh
docker build . -t zephyr-server
docker run -it -p 3000:3000 -e ZEPHYR_STORAGE_NAME=$(../deploy/getsetting instance_name) -e ZEPHYR_STORAGE_KEY=$(../deploy/getsetting storage_key) zephyr-server
