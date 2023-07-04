#!/bin/sh
docker build . -t zephyr-server
docker run -it -p 3000:3000 zephyr-server
