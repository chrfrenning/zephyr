from flask import Flask, jsonify, request, abort, send_file, render_template

import os
import json
import copy
import uuid
import subprocess
import numpy as np
from datetime import datetime, timedelta
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)
from azure.data.tables import TableClient
import shortuuid

app = Flask(__name__)

@app.route("/api")
def api():
    json = {
        "application": "zephyr/1.0",
        "version": "1.0",
        "api": {
            "matrix": {
                "endpoint": "/api/matrix",
                "method": "GET",
                "format": "json",
                "help": "Returns a random matrix."
            }
        }
    }
    return jsonify(json)

@app.route("/api/matrix", methods=["GET", "POST"])
def matrix():
   # create a random matrix with numpy and return in json format
    matrix = np.random.rand(30,30).tolist()
    return jsonify(matrix)

@app.route('/')
def home():
    return render_template('index.html')

def getStorageAccountUrlAndKey():
    # Get the storage account name and key from the environment variables
    storageAccountName = os.environ.get('ZEPHYR_STORAGE_NAME')
    storageAccountKey = os.environ.get('ZEPHYR_STORAGE_KEY')
    return storageAccountName, storageAccountKey

@app.route('/api/diagnostics', methods=['GET'])
def diagnostics():
    # Get the storage account name and key
    storageAccountName, storageAccountKey = getStorageAccountUrlAndKey()

    return jsonify({
        'storageAccountName': storageAccountName,
        'storageAccountKey': storageAccountKey
    })

class UserIdentity:
    def __init__(self, id, uname):
        self.id = id
        self.uname = uname

def getUserIdentity():
    # TODO: Implement authentication, for now return a phony object with user id = 0
    return UserIdentity(id=0, uname='dataninja')

def insert_into_azure_table(storage_account_name, table_name, account_key, entity):
    # Connect to the table client
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Insert the entity
    table_client.create_entity(entity=entity)

def getTableNameForDatasetRecords():
    return 'datasets' # TODO: Parameterize

def createDatasetMetadataRecord(blobId, sasToken, filename, userIdentity):
    # create an entry in azure table storage with the blobId, sasToken, filename, userIdentity and status='pending'
    # the table name is 'datasets'
    
    partition_key = shortuuid.random(length=3)
    short_id = partition_key + '-' + shortuuid.random(length=7)

    entity = {
        'PartitionKey': partition_key,
        'RowKey': short_id,
        'blobId': blobId,
        'sasToken': sasToken,
        'filename': filename,
        'userId': userIdentity.id,
        'status': 'pending'
    }

    storage_account_name, account_key = getStorageAccountUrlAndKey()
    insert_into_azure_table(storage_account_name, getTableNameForDatasetRecords(), account_key, entity)
    return short_id

def getDatasetDestinationUri(uid, id):
    return f'/u/{uid.uname}/{id}'

@app.route('/api/get-token', methods=['GET'])
def token():
    # Get filename from client
    original_filename = request.args.get("fn")
    if original_filename is None:
        abort(400, "Missing filename (fn query parameter)")
        
    # TODO: Map the unique id, user, and filename somewhere
    uid = getUserIdentity()

    # Get the storage account name and key
    storageAccountName, storageAccountKey = getStorageAccountUrlAndKey()
    
    # Create a SAS token for upload to a unique file name in the storage account
    blob_id, uri = createUploadUriWithToken(storageAccountName, storageAccountKey)
    
    # Create a placeholder metadata record
    metadata_id = createDatasetMetadataRecord(blobId=blob_id, sasToken=uri, filename=original_filename, userIdentity=uid)

    return jsonify({
        'uri': uri,
        #'id': id,
        'dest': getDatasetDestinationUri(uid, id)
    })

def getContainerNameForUploads():
    return 'original-data' # TODO: Parameterize

def createUploadUriWithToken(storageAccountName, storageAccountKey):
    # Blobname
    blobName = str(uuid.uuid4())
    # Create a SAS token that expires in an hour
    tokenExpiry = datetime.utcnow() + timedelta(hours=1)
    # Create a SAS token to upload a file to the storage account
    sasToken = generate_blob_sas(
        account_name=storageAccountName,
        container_name=getContainerNameForUploads(),
        blob_name=blobName,
        account_key=storageAccountKey,
        permission=BlobSasPermissions(read=True, write=True),
        expiry=tokenExpiry
        
    )
    # compose full url with token
    return blobName, f'https://{storageAccountName}.blob.core.windows.net/{getContainerNameForUploads()}/{blobName}?{sasToken}'


if __name__ == "__main__":
    app.run(debug = True, host = "0.0.0.0", port = 3000)