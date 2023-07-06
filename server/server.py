from flask import Flask, jsonify, request, abort, send_file, render_template, redirect

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
            },
            "get-token": {
                "endpoint": "/api/get-token",
                "params": [
                    { "name": "fn", "desc": "original file name", "type": "string", "required": True }
                ],
                "method": "GET",
                "format": "json",
                "help": "Returns id and token to upload a new file."
            },
            "datasets": {
                "endpoint": "/datasets",
                "method": "GET",
                "format": "json",
                "help": "Returns id and token to upload a new file."
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

def get_storage_account_url_and_key():
    # Get the storage account name and key from the environment variables
    storageAccountName = os.environ.get('ZEPHYR_STORAGE_NAME')
    storageAccountKey = os.environ.get('ZEPHYR_STORAGE_KEY')
    return storageAccountName, storageAccountKey

class UserIdentity:
    def __init__(self, id, uname):
        self.id = id
        self.uname = uname

def get_user_identity():
    # TODO: Implement authentication, for now return a phony object with user id = 0
    return UserIdentity(id=0, uname='dataninja')

def insert_into_azure_table(storage_account_name, table_name, account_key, entity):
    # Connect to the table client
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Insert the entity
    table_client.create_entity(entity=entity)

def get_tablename_for_dataset_records():
    return 'datasets' # TODO: Parameterize

def create_unique_metadata_id():
    partition_key = shortuuid.random(length=3)
    short_id = partition_key + '-' + shortuuid.random(length=7)
    return partition_key, short_id

def get_partition_key_from_metadata_id(metadata_id):
    return metadata_id.split('-')[0]

def create_dataset_metadata_record(blobId, sasToken, filename, userIdentity, metadata_id=None):
    # create an entry in azure table storage with the blobId, sasToken, filename, userIdentity and status='pending'
    # the table name is 'datasets'
    
    partition_key, short_id = create_unique_metadata_id()
    if metadata_id is not None:
        partition_key = get_partition_key_from_metadata_id(metadata_id)
        short_id = metadata_id

    entity = {
        'PartitionKey': partition_key,
        'RowKey': short_id,
        'blobId': blobId,
        'sasToken': sasToken,
        'filename': filename,
        'userId': userIdentity.id,
        'status': 'pending',
        'name' : filename,
        'desc' : 'A dataset',
        'date' : datetime.utcnow().isoformat(),
        'tags' : ''
    }

    storage_account_name, account_key = get_storage_account_url_and_key()
    insert_into_azure_table(storage_account_name, get_tablename_for_dataset_records(), account_key, entity)
    return short_id

def get_dataset_destination_uri(uid, id):
    return f'/u/{uid.uname}/{id}'

@app.route('/api/get-token', methods=['GET'])
def token():
    # Get filename from client
    original_filename = request.args.get("fn")
    if original_filename is None:
        abort(400, "Missing filename (fn query parameter)")
        
    # TODO: Map the unique id, user, and filename somewhere
    uid = get_user_identity()

    # Get the storage account name and key
    storageAccountName, storageAccountKey = get_storage_account_url_and_key()

    # Create metadata id
    _, metadata_id = create_unique_metadata_id()
    
    # Create a SAS token for upload to a unique file name in the storage account
    blob_id, uri = create_upload_uri_with_token(storageAccountName, storageAccountKey, metadata_id)
    
    # Create a placeholder metadata record
    metadata_id = create_dataset_metadata_record(blobId=blob_id, sasToken=uri, filename=original_filename, userIdentity=uid, metadata_id=metadata_id)

    return jsonify({
        'uri': uri,
        'id': metadata_id,
        'dest': get_dataset_destination_uri(uid, metadata_id)
    })

def get_container_name_for_uploads():
    return 'original-data' # TODO: Parameterize

def create_upload_uri_with_token(storage_account_name, storage_account_key, metadata_id):
    # Blobname
    blob_id = str(uuid.uuid4())
    blob_name = f'{metadata_id}/{blob_id}'
    # Create a SAS token that expires in an hour
    token_expiry = datetime.utcnow() + timedelta(hours=1)
    # Create a SAS token to upload a file to the storage account
    sas_token = generate_blob_sas(
        account_name=storage_account_name,
        container_name=get_container_name_for_uploads(),
        blob_name=blob_name,
        account_key=storage_account_key,
        permission=BlobSasPermissions(read=True, write=True),
        expiry=token_expiry
        
    )
    # compose full url with token
    return blob_name, f'https://{storage_account_name}.blob.core.windows.net/{get_container_name_for_uploads()}/{blob_name}?{sas_token}'

def create_download_uri_with_sas(storage_account_name, storage_account_key, blob_id):
    blob_name = f'{blob_id}'
    # Create a SAS token that expires in an hour
    token_expiry = datetime.utcnow() + timedelta(hours=24)
    sas_token = generate_blob_sas(
        account_name=storage_account_name,
        container_name=get_container_name_for_uploads(),
        blob_name=blob_name,
        account_key=storage_account_key,
        permission=BlobSasPermissions(read=True),
        expiry=token_expiry
    )
    # compose full url with token
    return f'https://{storage_account_name}.blob.core.windows.net/{get_container_name_for_uploads()}/{blob_name}?{sas_token}'

def get_username_from_userid(user_id):
    return 'dataninja' # TODO: Implement

def list_all_datasets():
    account_name, account_key = get_storage_account_url_and_key()
    # get all records from the datasets table
    table_name = get_tablename_for_dataset_records()
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)
    entities = table_client.list_entities()
    
    # pick only the ones with status='complete'
    # return only RowKey, filename, userId
    return [ {
        'id'        : entity['RowKey'],
        'filename'  : entity['filename'],
        'uid'       : entity['userId'],
        'uname'     : get_username_from_userid(entity['userId']),
        'name'      : entity['name'],
        'desc'      : entity['desc'],
        'date'      : entity['date'],
        'tags'      : entity['tags'],
        'blob_id'   : entity['blobId'],
        } for entity in entities if entity['status'] != 'deleted' ]


@app.route('/datasets', methods=['GET'])
def datasets():
    # if accept header is only json, return json
    accept_header = request.headers.get('Accept')
    if accept_header is not None and accept_header == 'application/json':
        # Get all datasets from the datasets table
        datasets = list_all_datasets()

        # Return the datasets as json
        return jsonify(datasets)
    else:
        # Return the datasets as html
        return render_template('datasets.html', datasets=list_all_datasets())

@app.route('/datasets/top', methods=['GET'])
def top_datasets():
    return datasets()

@app.route('/datasets/<id>', methods=['GET'])
def dataset(id):
    datasets = list_all_datasets()
    dataset = next((dataset for dataset in datasets if dataset['id'] == id), None)
    if dataset is None:
        abort(404, f"Dataset with id {id} not found")
    print(dataset)
    # if accept header is only json, return json
    accept_header = request.headers.get('Accept')
    if accept_header is not None and accept_header == 'application/json':
        # Return the datasets as json
        return jsonify(dataset)
    else:
        # Return the datasets as html
        download_uri = create_download_uri_with_sas(*get_storage_account_url_and_key(), dataset['blob_id'])
        report_json_uri = create_download_uri_with_sas(*get_storage_account_url_and_key(), dataset['id'] + '/ydata-report.json')
        print(report_json_uri)
        return render_template('dataset.html', dataset=dataset, download_uri=f'/datasets/{id}.raw', report_uri=f'/datasets/{id}.report', data_uri=report_json_uri)
    
def update_azure_table(storage_account_name, account_key, table_name, entity):
    # Connect to the table client
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Insert the entity
    table_client.update_entity(mode='merge', entity=entity)

@app.route('/datasets/<id>', methods=['DELETE'])
def delete_dataset(id):
    datasets = list_all_datasets()
    dataset = next((dataset for dataset in datasets if dataset['id'] == id), None)
    if dataset is None:
        abort(404, f"Dataset with id {id} not found")
    # TODO: Delete ydata-report.
    # TODO: Delete dataset metadata.
    # TODO: Delete dataset blob.
    # update status to deleted
    dataset['status'] = 'deleted'
    dataset['PartitionKey'] = get_partition_key_from_metadata_id(id)
    dataset['RowKey'] = id
    update_azure_table(*get_storage_account_url_and_key(), get_tablename_for_dataset_records(), dataset)
    return jsonify({ 'status': 'ok' })
    
@app.route('/datasets/<id>.raw', methods=['GET'])
def dataset_raw(id):
    datasets = list_all_datasets()
    dataset = next((dataset for dataset in datasets if dataset['id'] == id), None)
    if dataset is None:
        abort(404, f"Dataset with id {id} not found")
    download_uri = create_download_uri_with_sas(*get_storage_account_url_and_key(), dataset['blob_id'])
    return redirect(download_uri, code=302)

# SUGGESTION: Converters, return data as CSV, JSON, Excel, etc.
    
@app.route('/datasets/<id>.report', methods=['GET'])
def dataset_report(id):
    datasets = list_all_datasets()
    dataset = next((dataset for dataset in datasets if dataset['id'] == id), None)
    if dataset is None:
        abort(404, f"Dataset with id {id} not found")
    # Download ydata-report.html from blob storage
    account_name, account_key = get_storage_account_url_and_key()
    container_name = get_container_name_for_uploads()
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(container_name, f'{id}/ydata-report.html')
    blob_content = blob_client.download_blob().readall()
    # return blob_content to client
    return blob_content

@app.route('/datasets/<id>.report.json', methods=['GET'])
def dataset_report_json(id):
    datasets = list_all_datasets()
    dataset = next((dataset for dataset in datasets if dataset['id'] == id), None)
    if dataset is None:
        abort(404, f"Dataset with id {id} not found")
    # Download ydata-report.html from blob storage
    account_name, account_key = get_storage_account_url_and_key()
    container_name = get_container_name_for_uploads()
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(container_name, f'{id}/ydata-report.json')
    blob_content = blob_client.download_blob().readall()
    # return blob_content to client
    return blob_content, 200, {'Content-Type': 'application/json'}


if __name__ == "__main__":
    app.run(debug = True, host = "0.0.0.0", port = 3000)