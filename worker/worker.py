import os
import json
import copy
import uuid
import shortuuid
import subprocess
import base64
import numpy as np
from datetime import datetime, timedelta

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

def getStorageAccountUrlAndKey():
    # Get the storage account name and key from the environment variables
    storageAccountName = os.environ.get('ZEPHYR_STORAGE_NAME')
    storageAccountKey = os.environ.get('ZEPHYR_STORAGE_KEY')
    return storageAccountName, storageAccountKey

def get_message_from_queue(account_name: str, account_key: str, queue_name: str):
    queue_service_client = QueueServiceClient(account_url=f"https://{account_name}.queue.core.windows.net", credential=account_key)
    queue_client = queue_service_client.get_queue_client(queue_name)
    # Peek at messages in the queue
    messages = queue_client.peek_messages(max_messages=10)

    content = []
    for peeked_message in messages:
        #print("Peeked message: " + peeked_message.content)
        content.append( peeked_message.content )
    return content

def subjectToBlobUri(subject):
    # subject is in the form of /blobServices/default/containers/<container>/blobs/<blob>
    # we need to convert this to https://<storageaccount>.blob.core.windows.net/<container>/<blob>
    account_name, _ = getStorageAccountUrlAndKey()
    print(subject.split('/'))
    return f'https://{account_name}.blob.core.windows.net/{subject.split("/")[4]}/{subject.split("/")[6]}'

def processQueue():
    account_name, account_key = getStorageAccountUrlAndKey()
    # retrieve a message from the 'ingestion' queue
    # if there is a message, process it
    msg = get_message_from_queue(account_name, account_key, getIngestionQueueName())
    for m in msg:
        decoded_message = base64.b64decode(m).decode('utf-8')
        data = json.loads(decoded_message)
        if data['eventType'] == 'Microsoft.Storage.BlobCreated':
            bloburi = data['subject']
            print(f'BlobCreated: {subjectToBlobUri(bloburi)}')
            processBlob(subjectToBlobUri(bloburi))

def download_blob(account_name: str, account_key: str, container_name: str, blob_name: str, download_path: str):
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    # Download the blob to a file
    with open(download_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

def getContainerNameForUploads():
    return 'original-data' # TODO: Parameterize

def processBlob(bloburi):
    # download the blob
    account_name, account_key = getStorageAccountUrlAndKey()
    container_name = getContainerNameForUploads()
    blob_name = bloburi.split('/')[-1]
    download_path = f'/tmp/{blob_name}'
    download_blob(account_name, account_key, container_name, blob_name, download_path)
    # run the model
    # upload the results
    



# main
if __name__ == "__main__":
    processQueue()