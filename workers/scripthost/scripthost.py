import os
import json
import copy
import time
import uuid
import shortuuid
import subprocess
import base64
import numpy as np
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)

from azure.storage.queue import (
    QueueServiceClient,
    QueueClient,
    QueueMessage
)
from azure.data.tables import TableClient


def get_ingestion_queue_name():
    return 'scripthost' # TODO: Parameterize this

def get_container_name_for_uploads():
    return 'original-data' # TODO: Parameterize

def get_table_name_for_dataset_records():
    return 'datasets' # TODO: Parameterize

def get_storage_account_url_and_key():
    # Get the storage account name and key from the environment variables
    storageAccountName = os.environ.get('ZEPHYR_STORAGE_NAME')
    storageAccountKey = os.environ.get('ZEPHYR_STORAGE_KEY')
    return storageAccountName, storageAccountKey

def process_queue():
    account_name, account_key = get_storage_account_url_and_key()
    queue_service_client = QueueServiceClient(account_url=f"https://{account_name}.queue.core.windows.net", credential=account_key)
    queue_client = queue_service_client.get_queue_client(get_ingestion_queue_name())
    
    # we're only doing one job per container for security reasons (script isolation)
    msg = queue_client.receive_message(visibility_timeout=300)
    # if there is a message, process it
    if msg:
        print(msg)
        decoded_message = base64.b64decode(msg.content).decode('utf-8')
        print(decoded_message)
        # data = json.loads(decoded_message)
        # TODO: handle the message
        # delete the message from the queue
        queue_client.delete_message(msg)
    else:
        print(f'no messages in the {get_ingestion_queue_name()} queue')

def download_blob(account_name: str, account_key: str, container_name: str, metadata_id : str, blob_name: str, download_path: str):
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(container_name, f'{metadata_id}/{blob_name}')
    # Download the blob to a file
    with open(download_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

def insert_into_azure_table(storage_account_name, table_name, account_key, entity):
    # Connect to the table client
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Insert the entity
    table_client.create_entity(entity=entity)

def update_azure_table(storage_account_name, table_name, account_key, entity):
    # Connect to the table client
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Insert the entity
    table_client.update_entity(mode='merge', entity=entity)

# find single record by partionkey and rowkey
def find_dataset_by_id(id):
    account_name, account_key = get_storage_account_url_and_key()
    # get all records from the datasets table
    table_name = get_table_name_for_dataset_records()
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)
    entity = table_client.get_entity(partition_key=get_partition_key_from_id(id), row_key=id)
    return entity

# main
if __name__ == "__main__":
    process_queue()