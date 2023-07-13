import os
import signal
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



# Global variables, hell yeah ;)
stop_signal = False
queue_vis_timeout = 5



# Functions and stuff, this is a mess but keep with me for now
 
def get_scripthost_queue_name():
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
    queue_client = queue_service_client.get_queue_client(get_scripthost_queue_name())
    
    time_wait = 0.5
    global stop_signal
    while not stop_signal:
        msg = queue_client.receive_message(visibility_timeout=queue_vis_timeout)
        # if there is a message, process it
        if msg:
            # message on form
            # {
            #     "metadata_id": metadata_id,
            #     "blob_id": blob_id,
            #     "script": split_code_from_response(response),
            #     "chart_name": "chart3.png",
            #     "chart_description": vis["vis3"]
            # }
            print(msg.content)
            data = json.loads(msg.content)
            # base64 deocde data['script']
            script = base64.b64decode(data['script']).decode('utf-8')
            print(script)
            # TODO: handle the message
            download_blob(account_name, account_key, get_container_name_for_uploads(), data['metadata_id'], data['blob_id'], './sample.csv')
            # Write the script to a file
            with open('./script.py', 'w') as f:
                f.write(script)
            # Run the script
            try:
                result = subprocess.run(['python', './script.py'], check=True, capture_output=True, text=True)
                # log the output of the subprocess
                print('subprocess stdout:', result.stdout)
                print('subprocess stderr:', result.stderr)
                # TODO: upload the resulting chart.png to the result container
                # check if the file exists, otherwise we fail
                if os.path.isfile('./chart.png'):
                    upload_blob(account_name, account_key, get_container_name_for_uploads(), data['metadata_id'], data['chart_name'], './chart.png')
                    print("this might have succeeded...")
            except subprocess.CalledProcessError as e:
                print("Failed running script: " + e)
            # cleanup here, delete script.py, sample.csv and chart.png
            os.remove('./script.py') if os.path.isfile('./script.py') else None
            os.remove('./sample.csv') if os.path.isfile('./sample.csv') else None
            os.remove('./chart.png') if os.path.isfile('./chart.png') else None
            # update the dataset record in the table
            metadata = find_dataset_by_id(data['metadata_id'])
            if 'charts' in metadata:
                metadata['charts'] = json.loads(metadata['charts'])
            else:
                metadata['charts'] = []
            metadata['charts'].append({
                'name': data['chart_name'],
                'description': data['chart_description']
            })
            metadata['charts'] = json.dumps(metadata['charts'])
            update_azure_table(account_name, account_key, get_table_name_for_dataset_records(), metadata)
            # delete the message from the queue
            queue_client.delete_message(msg)
        else:
            print(f'no messages in the {get_scripthost_queue_name()} queue, waiting a bit...')
            time.sleep(time_wait)

    print('Stopping gracefully after sigterm signal.')

def upload_blob(account_name: str, account_key: str, container_name: str, metadata_id : str, blob_name: str, file_name: str):
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(container_name, f'{metadata_id}/{blob_name}')
    with open(file_name, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

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

def update_azure_table(storage_account_name, account_key, table_name, entity):
    # Connect to the table client
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Insert the entity
    table_client.update_entity(mode='merge', entity=entity)

def get_partition_key_from_id(id):
    return id.split('-')[0]

# find single record by partionkey and rowkey
def find_dataset_by_id(id):
    account_name, account_key = get_storage_account_url_and_key()
    # get all records from the datasets table
    table_name = get_table_name_for_dataset_records()
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)
    entity = table_client.get_entity(partition_key=get_partition_key_from_id(id), row_key=id)
    return entity

def receive_termination_signal(sig_num, frame):
    print('Received stop signal {}, completing current job then stopping. '.format(sig_num))
    global stop_signal
    stop_signal = True
    return

# main
if __name__ == "__main__":
    # Shut me down with sigterm
    print("New file handling worker started, pid is ", os.getpid(), " send sigterm with 'kill -{} <pid>' or CTRL-C to stop me gracefully.".format(signal.SIGTERM))
    signal.signal(signal.SIGTERM, receive_termination_signal)
    signal.signal(signal.SIGINT, receive_termination_signal)

    process_queue()