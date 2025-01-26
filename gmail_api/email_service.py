from googleapiclient.discovery import build
from typing import List, Dict, Any, Optional
import base64
import email

class GmailService:
    def __init__(self, credentials):
        """Initialize Gmail service with credentials."""
        self.service = build('gmail', 'v1', credentials=credentials)

    def get_emails(self, query: str = '', max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve emails from Gmail based on query.
        
        Args:
            query: Search query string
            max_results: Maximum number of emails to retrieve
            
        Returns:
            List of email messages with their content
        """
        try:
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Parse email content
                payload = msg['payload']
                headers = payload.get('headers', [])
                
                # Extract email metadata
                email_data = {
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'labelIds': msg.get('labelIds', []),
                    'subject': '',
                    'from': '',
                    'date': '',
                    'body': ''
                }

                # Get headers
                for header in headers:
                    name = header['name'].lower()
                    if name == 'subject':
                        email_data['subject'] = header['value']
                    elif name == 'from':
                        email_data['from'] = header['value']
                    elif name == 'date':
                        email_data['date'] = header['value']

                # Get email body
                if 'parts' in payload:
                    parts = payload['parts']
                    for part in parts:
                        if part['mimeType'] == 'text/plain':
                            data = part['body'].get('data', '')
                            if data:
                                text = base64.urlsafe_b64decode(data).decode()
                                email_data['body'] += text
                else:
                    # Handle messages with no parts
                    data = payload['body'].get('data', '')
                    if data:
                        text = base64.urlsafe_b64decode(data).decode()
                        email_data['body'] += text

                emails.append(email_data)

            return emails

        except Exception as e:
            print(f"Error retrieving emails: {str(e)}")
            return []

    def create_label(self, label_name: str) -> str:
        """
        Create a new label in Gmail.
        
        Args:
            label_name: Name of the label to create
            
        Returns:
            Label ID if successful, None otherwise
        """
        try:
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            
            return created_label['id']
        
        except Exception as e:
            print(f"Error creating label: {str(e)}")
            return None

    def add_label_to_email(self, email_id: str, label_ids: List[str]) -> bool:
        """
        Add labels to a specific email.
        
        Args:
            email_id: ID of the email to modify
            label_ids: List of label IDs to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'addLabelIds': label_ids}
            ).execute()
            return True
            
        except Exception as e:
            print(f"Error adding labels: {str(e)}")
            return False
