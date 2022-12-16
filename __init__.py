import os
import datetime
import logging
import base64
import requests
import json
from opencensus.ext.azure.log_exporter import AzureLogHandler
from azure.storage.blob import BlobServiceClient, ContainerClient
import azure.functions as func


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')
    # Create the BlobServiceClient object
    creds=os.getenv("ACCOUNT_KEY")
    account_url = "https://lakeciehknalis.blob.core.windows.net/"

    blob_service_client = BlobServiceClient(account_url, credential=creds)   

    # Create a unique name for the container
    container_name = "employees"
    conn=os.getenv("CONNECTION_STRING")
    container = ContainerClient.from_connection_string(conn, container_name)

    # Create the container
    if not container.exists():
        blob_service_client.create_container(container_name) 
    resultUrl = create_onedrive_directdownload("https://knowit.sharepoint.com/:x:/r/sites/org-165-Internal/Shared%20Documents/Semesterlista%20SOL%202021%20-%20Copy.xlsx?d=w49625d1c2dbe4e44a66490f7cc6da5ef&csf=1&web=1&e=nSsj4w")
    r = requests.get(resultUrl)
    # Create a blob client using the local file name as the name for the blob 
    now = datetime.now()
    blob_name = now.strftime("employees_copy%m%d%Y-%H:%M:%S.xlsx")
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    # Upload the created file
    blob_client.upload_blob(json.dumps(r))

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

def create_onedrive_directdownload (onedrive_link):
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl