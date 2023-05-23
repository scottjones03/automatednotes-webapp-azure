from azure.storage.blob import BlobServiceClient
from flask import current_app
import os
from queue import Queue
import ast

class AzureBlobStorageManager:
    CREDENTIALS = 'N7vtqh8Ud9w2eelF2T+WVochoMHqfNorJNrsBbBq/FgDA9RELp31ldATWYksizlQc3BdTL0CiNCT+AStj147bQ=='
    URL = 'https://automatednotes.blob.core.windows.net/'
    @staticmethod
    def upload_file(blob_name: str, data):
        blob_service_client = BlobServiceClient(account_url=AzureBlobStorageManager.URL, credential=AzureBlobStorageManager.CREDENTIALS)
        blob_service_client.get_container_client('automatednotes').upload_blob(blob_name, data, overwrite=True)

    @staticmethod
    def download_file(blob_name: str, file_name: str):
        local_destination_path = os.path.join(os.environ.get('TEXT_FOLDER'), file_name)
        
        blob_service_client = BlobServiceClient(account_url=AzureBlobStorageManager.URL, credential=AzureBlobStorageManager.CREDENTIALS)

        with open(local_destination_path, 'wb') as file:
            blob_client = blob_service_client.get_blob_client(container='automatednotes', blob=blob_name)
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())
        return local_destination_path
    
    @staticmethod
    def update_jobs(jobqueue: Queue):
        blob_service_client = BlobServiceClient(account_url=AzureBlobStorageManager.URL, credential=AzureBlobStorageManager.CREDENTIALS)
        
        container_client = blob_service_client.get_container_client('automatednotes')
        for blob_name in container_client.list_blobs(name_starts_with='TODO'):
            blob_client = blob_service_client.get_blob_client(container='automatednotes', blob=blob_name)
            download_stream = blob_client.download_blob()
            data=download_stream.readall().decode()
            l=ast.literal_eval(data)
            jobqueue.put((blob_name['name'], l))
        return
    
    def delete_blob(blob_name, blob_name_job):
        blob_service_client = BlobServiceClient(account_url=AzureBlobStorageManager.URL, credential=AzureBlobStorageManager.CREDENTIALS)
        blob_client = blob_service_client.get_blob_client(container=AzureBlobStorageManager.URL, blob=blob_name)
        blob_client.delete_blob()
        blob_client = blob_service_client.get_blob_client(container=AzureBlobStorageManager.URL, blob=blob_name_job)
        blob_client.delete_blob()


