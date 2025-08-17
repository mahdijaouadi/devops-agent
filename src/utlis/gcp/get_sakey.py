import os
import json
from google.cloud import storage
from google.oauth2 import service_account
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))

def download_save_sakey(url,session_id):
    url=url.split('//')
    url=url[1]
    url=url.split('/')
    sa_key_json = os.getenv('SA_KEY')
    if not sa_key_json:
        raise ValueError("Environment variable SA_KEY not set")

    sa_info = json.loads(sa_key_json)

    # Create credentials from the service account info
    credentials = service_account.Credentials.from_service_account_info(sa_info)

    # Initialize the client with explicit credentials
    client = storage.Client(credentials=credentials, project=sa_info.get("project_id"))

    # GCS file info
    bucket_name = url[0]
    blob_path = '/'.join(url[1:]) 

    # Local destination to save the file
    local_destination = os.path.abspath(os.path.join(current_dir, "..", "..", "tmp",session_id, "sa_key.json"))

    # Get bucket and blob
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # Download the blob contents
    blob.download_to_filename(local_destination)
    logger.info(f"Downloaded gs://{bucket_name}/{blob_path} to {local_destination}")