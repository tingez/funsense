import os
import pickle
import traceback
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import hydra
from hydra import initialize, compose

def get_gmail_service():
    """Get Gmail API service instance."""
    try:
        with initialize(version_base=None, config_path="../conf"):
            cfg = compose(config_name="gmail")
            
        creds = None
        token_path = cfg.auth.token_path
        credentials_path = cfg.auth.credentials_path
        scopes = cfg.auth.scopes[0]  # Get the first scope as a string
        
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, [scopes])
                
                print("Please make sure the following redirect URI is configured in your Google Cloud Console:")
                print("http://localhost:8081/")
                print("Waiting for authentication...")
                
                try:
                    creds = flow.run_local_server(
                        port=8081,
                        success_message="Authentication successful! You can close this window.",
                        open_browser=True
                    )
                except Exception as e:
                    print(f"Authentication failed: {str(e)}")
                    print("Please verify the redirect URI 'http://localhost:8081/' is configured in your Google Cloud Console")
                    print("Steps to configure:")
                    print("1. Go to https://console.cloud.google.com")
                    print("2. Select your project")
                    print("3. Go to 'APIs & Services' > 'Credentials'")
                    print("4. Edit your OAuth 2.0 Client ID")
                    print("5. Add 'http://localhost:8081/' to 'Authorized redirect URIs'")
                    print("6. Click 'Save' and try again")
                    raise
            
            # Save the credentials for the next run
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        return creds

    except Exception as e:
        print(f"Error in Gmail authentication: {str(e)}")
        print("Stack trace:")
        print(traceback.format_exc())
        return None
