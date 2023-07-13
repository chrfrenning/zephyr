#!/bin/sh
docker build . -t zephyr-ingestion
docker run -it -e ZEPHYR_STORAGE_NAME=$(../../deploy/getsetting instance_name) -e ZEPHYR_STORAGE_KEY=$(../../deploy/getsetting storage_key) -e ZEPHYR_OPENAI_ORG=$(../../deploy/getsetting openai_org) -e ZEPHYR_OPENAI_KEY=$(../../deploy/getsetting openai_key) -e ZEPHYR_OPENAI_MODEL=$(../../deploy/getsetting openai_model) zephyr-ingestion
