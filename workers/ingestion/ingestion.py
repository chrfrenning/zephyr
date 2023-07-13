import os
import signal
import json
import time
import base64
import numpy as np
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from ydata_profiling import ProfileReport
import gpt as generator

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



# Functions and stuff, this is a mess but keep with me for now

def get_ingestion_queue_name():
    return 'ingestion' # TODO: Parameterize this

def get_scripthost_queue_name():
    return 'scripthost' # TODO: Parameterize this

def get_storage_account_url_and_key():
    # Get the storage account name and key from the environment variables
    storageAccountName = os.environ.get('ZEPHYR_STORAGE_NAME')
    storageAccountKey = os.environ.get('ZEPHYR_STORAGE_KEY')
    return storageAccountName, storageAccountKey

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
    queue_service_client = QueueServiceClient(account_url=f"https://{account_name}.queue.core.windows.net", credential=account_key)
    queue_client = queue_service_client.get_queue_client(get_ingestion_queue_name())
    
    # Peek at messages in the queue
    time_wait = 0.5
    wait_cycles = 5
    wait_c = 0
    global stop_signal
    while stop_signal == False:
        msg = queue_client.receive_message(visibility_timeout=20)#300)
        # if there is a message, process it
        if msg:
            print(msg)
            decoded_message = base64.b64decode(msg.content).decode('utf-8')
            data = json.loads(decoded_message)
            if data['eventType'] == 'Microsoft.Storage.BlobCreated':
                bloburi = data['subject']
                blob_id, metadata_id = subject_to_ids(bloburi)
                if not '.' in blob_id:
                    blob_url = subject_to_blob_uri(bloburi)
                    process_blob(metadata_id, blob_id, blob_url)
                else:
                    print('Ignoring file with extension')
            else:
                print('Unknown event type')
            # delete the message from the queue
            queue_client.delete_message(msg)
        else:
            # no more messages to process, let the container stop
            print('No more messages, waiting a bit')
            time.sleep(time_wait)
            # wait_c += 1
            # if wait_c > wait_cycles:
            #     print('No more messages to process, exiting')
            #     break
    print('Received sigterm, leaving process queue loop')

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

def get_table_name_for_dataset_records():
    return 'datasets' # TODO: Parameterize

def process_blob(metadata_id, blob_id, bloburi):
    account_name, account_key = get_storage_account_url_and_key()
    # get the metadata
    metadata = find_dataset_by_id(metadata_id)
    print(metadata)
    # update the metadata to status=processing
    metadata['status'] = 'processing'
    update_azure_table(account_name, account_key, get_table_name_for_dataset_records(), metadata)
    # download the blob
    download_path = do_download_blob(metadata_id, blob_id)
    # what type of file
    extension = metadata['filename'].split('.')[-1]
    # if csv
    if extension == 'csv':
        # load into dataframe
        df = pd.read_csv(download_path)
        # profile the data using ydata
        create_profile_report(metadata_id, df)
        # analyze using gpt
        do_science_stuff(metadata_id, blob_id, metadata, df)
        # update_azure_table(account_name, account_key, get_table_name_for_dataset_records(), metadata) #redundant
        # update the metadata to status=complete
        metadata['status'] = 'complete'
        update_azure_table(account_name, account_key, get_table_name_for_dataset_records(), metadata)
    else:
        print('Ignoring file with unknown extension')
        metadata['status'] = 'ignored'
        update_azure_table(account_name, account_key, get_table_name_for_dataset_records(), metadata)

def do_download_blob(metadata_id, blob_id):
    account_name, account_key = get_storage_account_url_and_key()
    download_path = f'/tmp/{blob_id}'
    download_blob(account_name, account_key, get_container_name_for_uploads(), metadata_id, blob_id, download_path)
    return download_path
    
def create_profile_report(metadata_id, df):
    profile = ProfileReport(df, title="Profiling Report")
    profile.to_file(f'/tmp/{metadata_id}.html')
    profile.to_file(f'/tmp/{metadata_id}.json')
    # upload file to blob storage
    account_name, account_key = get_storage_account_url_and_key()
    blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
    blob_client = blob_service_client.get_blob_client(get_container_name_for_uploads(), f'{metadata_id}/ydata-report.html')
    with open(f'/tmp/{metadata_id}.html', "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    blob_client = blob_service_client.get_blob_client(get_container_name_for_uploads(), f'{metadata_id}/ydata-report.json')
    with open(f'/tmp/{metadata_id}.json', "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    
def do_science_stuff(metadata_id, blob_id, metadata, df):
    # get a random sample with five rows of this data
    sample = df.sample(5)
    sample_json = sample.to_json(orient='records')

    # grounding
    grounding = f"""You are a Data Scientist. Help me understand and analyse a dataset I have in a CSV file.
    Here are the headers and five random rows in a JSON dump from Pandas: {sample_json}"""

    # describe the dataset
    chat = generator.Chat(grounding)
    question = "Describe the dataset in your own words."
    response = chat.complete(question)
    metadata["gpt_description"] = response

    # suggest visualisations
    prompt = """Suggest three visualizations for this dataset. 
                             
                Return the results in a json document formatted like this: 
                
                {\"vis1\": \"\", \"vis2\": \"\", \"vis3\": \"\"}
                
                Return ONLY the JSON document, nothing else."""
    response = chat.complete(prompt)
    metadata["gpt_visualisations"] = response
    vis = {}
    try:
        vis = json.loads(response)
    except:
        print("GPT failed to suggest visualisations in JSON format, ignoring...")
        return
    
    script_prompt = """Help me create a chart
    
    Description: {description}\n\n
    
    Write Python code to generate the visualisation described above. 
    You must use Pandas to load the data from the file 'sample.csv'.
    Use matplotlib to create a chart. Save the chart to 'chart.png'.
    Do not change the filenames in your code."""

    for v in vis.keys():
        description = vis[v]
        try:
            response = chat.complete(script_prompt.format(description=description))
            post_message_to_queue(get_scripthost_queue_name(), {
                "metadata_id": metadata_id,
                "blob_id": blob_id,
                "script": split_code_from_response_and_b64_encode(response),
                "chart_name": f"{v}.png",
                "chart_description": description
            })
        except:
            print("Failed to create visualisation " + v)

def split_code_from_response_and_b64_encode(response):
    code = response.split("```python")[1].split("```")[0]
    # base64 encode the code
    return base64.b64encode(code.encode('utf-8')).decode('utf-8')

def post_message_to_queue(queue_name, message):
    account_name, account_key = get_storage_account_url_and_key()
    queue_service_client = QueueServiceClient(account_url=f"https://{account_name}.queue.core.windows.net", credential=account_key)
    queue_client = queue_service_client.get_queue_client(queue_name)
    queue_client.send_message(json.dumps(message))

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

    # Start the main queue processing loop
    process_queue()