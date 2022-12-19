import os
from datetime import datetime, timezone 
import logging
import base64
import requests
import shutil
import json
import msal
import jwt
import pandas as pd
from azure.storage.blob import BlobServiceClient, ContainerClient
import azure.functions as func

accessToken = None 
requestHeaders = None 
tokenExpiry = None 
queryResults = None 
graphURI = 'https://graph.microsoft.com'

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.utcnow().replace(
        tzinfo=timezone.utc).isoformat()

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

    # Auth
    msgraph_auth()

    # Query
    queryResults = msgraph_request(graphURI +'/v1.0/users',requestHeaders)

    # Results to Dataframe
    try:
        df = pd.read_json(json.dumps(queryResults['value']))
        # set ID column as index
        df = df.set_index('id')
        print(str(df['displayName'] + " " + df['mail']))
    except:
        print(json.dumps(queryResults, indent=2))

    # resultUrl = create_onedrive_directdownload("https://knowit.sharepoint.com/:x:/r/sites/org-165-Internal/Shared%20Documents/Semesterlista%20SOL%202021%20-%20Copy.xlsx?d=w49625d1c2dbe4e44a66490f7cc6da5ef&csf=1&web=1&e=nSsj4w")
    # headers = {'content-type': 'application/octet-stream'}

    # r = requests.get(resultUrl, headers=headers, stream=True)
    # result_File = r.raw.read()

    # # Create a blob client using the local file name as the name for the blob 
    # now = datetime.now()
    # blob_name = now.strftime("employees_copy%m%d%Y-%H:%M:%S.xlsx")
    # blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    # # Upload the created file
    # blob_client.upload_blob(result_File)

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename

# REDACTED
def create_onedrive_directdownload (onedrive_link):
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl

def msgraph_auth():
    global accessToken
    global requestHeaders
    global tokenExpiry
    tenantID = 'e34d5777-07b1-4c5b-bbea-068c4139108c'
    authority = 'https://login.microsoftonline.com/' + tenantID
    clientID = '4aa12be5-1830-4ed1-8f4a-3b626ed6b303'
    clientSecret = 'Ljz8Q~ETSbGaR_RhxHgAzQ2pzJE_TFyjjMwVEasl'
    scope = ['https://graph.microsoft.com/.default','files.readwrite']

    app = msal.ConfidentialClientApplication(clientID, authority=authority, client_credential = clientSecret)

    try:
        accessToken = app.acquire_token_silent(scope, account=None)
        if not accessToken:
            try:
                accessToken = app.acquire_token_for_client(scopes=scope)
                if accessToken['access_token']:
                    print('New access token retreived....')
                    requestHeaders = {'Authorization': 'Bearer ' + accessToken['access_token']}
                else:
                    print('Error aquiring authorization token. Check your tenantID, clientID and clientSecret.')
            except:
                pass 
        else:
            print('Token retreived from MSAL Cache....')

        decodedAccessToken = jwt.decode(accessToken['access_token'], verify=False)
        accessTokenFormatted = json.dumps(decodedAccessToken, indent=2)
        print('Decoded Access Token')
        print(accessTokenFormatted)

        # Token Expiry
        tokenExpiry = datetime.fromtimestamp(int(decodedAccessToken['exp']))
        print('Token Expires at: ' + str(tokenExpiry))
        return
    except Exception as err:
        print(err)

def msgraph_request(resource,requestHeaders):
    # Request
    results = requests.get(resource, headers=requestHeaders).json()
    return results