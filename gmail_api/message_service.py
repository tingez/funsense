from typing import List, Dict, Any, Optional
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class MessageService:
    def __init__(self, service):
        """Initialize Message service with Gmail API service."""
        self.service = service

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

    def send_email(self, to: str, subject: str, body: str, 
                  cc: Optional[str] = None, bcc: Optional[str] = None) -> bool:
        """
        Send an email using Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            cc: Carbon copy recipients (optional)
            bcc: Blind carbon copy recipients (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

            msg = MIMEText(body)
            message.attach(msg)

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read by removing the UNREAD label.
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error marking message as read: {str(e)}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark an email as unread by adding the UNREAD label.
        
        Args:
            message_id: ID of the message to mark as unread
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error marking message as unread: {str(e)}")
            return False

    def trash_message(self, message_id: str) -> bool:
        """
        Move a message to trash.
        
        Args:
            message_id: ID of the message to trash
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error moving message to trash: {str(e)}")
            return False

    def untrash_message(self, message_id: str) -> bool:
        """
        Restore a message from trash.
        
        Args:
            message_id: ID of the message to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().untrash(
                userId='me',
                id=message_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error restoring message from trash: {str(e)}")
            return False

    def add_labels_to_message(self, message_id: str, label_ids: List[str]) -> bool:
        """
        Add labels to a specific message.
        
        Args:
            message_id: ID of the message to modify
            label_ids: List of label IDs to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': label_ids}
            ).execute()
            return True
        except Exception as e:
            print(f"Error adding labels: {str(e)}")
            return False

    def remove_labels_from_message(self, message_id: str, label_ids: List[str]) -> bool:
        """
        Remove labels from a specific message.
        
        Args:
            message_id: ID of the message to modify
            label_ids: List of label IDs to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': label_ids}
            ).execute()
            return True
        except Exception as e:
            print(f"Error removing labels: {str(e)}")
            return False

    def list_messages(self, query: str = None, max_results: int = None) -> List[Dict[str, Any]]:
        """
        List messages matching the specified query.
        
        Args:
            query: Search query (Gmail search syntax)
            max_results: Maximum number of messages to return (None for all)
            
        Returns:
            List of message objects containing id and threadId
        """
        try:
            messages = []
            page_token = None
            
            while True:
                request = self.service.users().messages().list(
                    userId='me',
                    q=query if query else '',
                    pageToken=page_token,
                    maxResults=min(max_results, 100) if max_results else 100
                )
                response = request.execute()
                batch = response.get('messages', [])
                
                if not batch:
                    break
                    
                messages.extend(batch)
                
                if max_results and len(messages) >= max_results:
                    messages = messages[:max_results]
                    break
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                    
            print(f"Found {len(messages)} messages matching query: {query}")
            return messages
            
        except Exception as e:
            print(f"Error listing messages: {str(e)}")
            return []
