#!/bin/sh
docker build . -t zephyr-server
docker run -it -p 3000:3000 -e ZEPHYR_STORAGE_NAME=$ZEPHYR_STORAGE_NAME -e ZEPHYR_STORAGE_KEY=$ZEPHYR_STORAGE_KEY zephyr-server
