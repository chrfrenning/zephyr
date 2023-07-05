import os
import json
import copy
import uuid
import shortuuid
import subprocess
import base64
import numpy as np
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from ydata_profiling import ProfileReport

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


def getIngestionQueueName():
    return 'ingestion' # TODO: Parameterize this

def get_storage_account_url_and_key():
    # Get the storage account name and key from the environment variables
    storageAccountName = os.environ.get('ZEPHYR_STORAGE_NAME')
    storageAccountKey = os.environ.get('ZEPHYR_STORAGE_KEY')
    return storageAccountName, storageAccountKey

def get_message_from_queue(account_name: str, account_key: str, queue_name: str):
    queue_service_client = QueueServiceClient(account_url=f"https://{account_name}.queue.core.windows.net", credential=account_key)
    queue_client = queue_service_client.get_queue_client(queue_name)
    # Peek at messages in the queue
    messages = queue_client.peek_messages(max_messages=10) 
    # TODO: actual dequeue and delete if successful

    content = []
    for peeked_message in messages:
        #print("Peeked message: " + peeked_message.content)
        content.append( peeked_message.content )
    return content

def subject_to_blob_uri(subject):
    # subject is in the form of /blobServices/default/containers/<container>/blobs/<blob>
    # we need to convert this to https://<storageaccount>.blob.core.windows.net/<container>/<blob>
    account_name, _ = get_storage_account_url_and_key()
    return f'https://{account_name}.blob.core.windows.net/{subject.split("/")[4]}/{subject.split("/")[6]}/{subject.split("/")[7]}'

def subject_to_ids(subject):
    blob_id = subject.split("/")[7]
    metadata_id = subject.split("/")[6]
    return blob_id, metadata_id

def process_queue():
    account_name, account_key = get_storage_account_url_and_key()
    # retrieve a message from the 'ingestion' queue
    # if there is a message, process it
    msg = get_message_from_queue(account_name, account_key, getIngestionQueueName())
    for m in msg:
        decoded_message = base64.b64decode(m).decode('utf-8')
        data = json.loads(decoded_message)
        if data['eventType'] == 'Microsoft.Storage.BlobCreated':
            bloburi = data['subject']
            blob_id, metadata_id = subject_to_ids(bloburi)
            blob_url = subject_to_blob_uri(bloburi)
            process_blob(metadata_id, blob_id, blob_url)

def download_blob(account_name: str, account_key: str, container_name: str, metadata_id : str, blob_name: str, download_path: str):
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(container_name, f'{metadata_id}/{blob_name}')
    # Download the blob to a file
    with open(download_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

def get_container_name_for_uploads():
    return 'original-data' # TODO: Parameterize

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

def list_all_datasets():
    account_name, account_key = get_storage_account_url_and_key()
    # get all records from the datasets table
    table_name = get_table_name_for_dataset_records()
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)
    entities = table_client.list_entities()
    
    # pick only the ones with status='complete'
    # return only RowKey, filename, userId
    return [{'id':entity['RowKey'],'filename':entity['filename'],'userId':entity['userId'],'desc':'This is a static description of a dataset with points for each observation and statistical significance that can lead to conclusions without bias and visually interesting representations.'} for entity in entities if entity['status'] == 'pending']

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

def get_table_name_for_dataset_records():
    return 'datasets' # TODO: Parameterize

def process_blob(metadata_id, blob_id, bloburi):
    account_name, account_key = get_storage_account_url_and_key()
    # get the metadata
    metadata = find_dataset_by_id(metadata_id)
    print(metadata)
    # update the metadata to status=processing
    metadata['status'] = 'processing'
    update_azure_table(account_name, get_table_name_for_dataset_records(), account_key, metadata)
    # download the blob
    account_name, account_key = get_storage_account_url_and_key()
    container_name = get_container_name_for_uploads()
    download_path = f'/tmp/{blob_id}'
    download_blob(account_name, account_key, container_name, metadata_id, blob_id, download_path)
    # what type of file
    extension = metadata['filename'].split('.')[-1]
    # if csv
    if extension == 'csv':
        # load into dataframe
        df = pd.read_csv(download_path)
        #df = pd.DataFrame(np.random.rand(100, 5), columns=["a", "b", "c", "d", "e"])
        profile = ProfileReport(df, title="Profiling Report")
        #print(profile.to_json())
        profile.to_file(f'/tmp/{metadata_id}.html')

    
    # upload the results
    # update the metadata to status=complete
    #metadata['status'] = 'complete'
    #update_azure_table(account_name, get_table_name_for_dataset_records(), account_key, metadata)
    
    



# main
if __name__ == "__main__":
    process_queue()