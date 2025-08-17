import os
import json
from google.cloud import storage
from google.oauth2 import service_account
import time
import jwt
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))

def get_github_app_private_key(url):
    """
    Downloads a GitHub App private key from a GCS URL and returns it as a string.
    """
    # Parse the GCS URL
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
    bucket_name = url[0]
    blob_path = url[1]
    # Get bucket and blob
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # Download the blob contents as bytes and decode to a string
    private_key_bytes = blob.download_as_bytes()
    private_key = private_key_bytes.decode('utf-8')
    
    print(f"Successfully downloaded private key from gs://{bucket_name}/{blob_path}")
    
    return private_key

def get_jwt(private_key: str, app_id: str) -> str:
    """Generate a JWT for the GitHub App using its private key."""
    now = int(time.time())
    payload = {"iat": now, "exp": now + 600, "iss": app_id}
    return jwt.encode(payload, private_key, algorithm="RS256")

def get_installation_token(jwt_token: str, installation_id: str) -> str:
    """Exchange the JWT for an installation access token."""
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    resp = requests.post(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data["token"]