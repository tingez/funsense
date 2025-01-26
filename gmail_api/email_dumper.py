import json
import os
import datetime
from typing import List, Dict, Any
import base64
from email import message_from_bytes
from email.message import EmailMessage
import email
from .label_service import LabelService
from .message_service import MessageService

class EmailDumper:
    def __init__(self, service):
        """Initialize EmailDumper with Gmail API service."""
        self.label_service = LabelService(service)
        self.message_service = MessageService(service)
        self.service = service

    def _parse_message_parts(self, parts, content: Dict[str, Any]):
        """Recursively parse message parts to extract content."""
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type.startswith('text/'):
                data = part.get('body', {}).get('data', '')
                if data:
                    text = base64.urlsafe_b64decode(data).decode()
                    if mime_type == 'text/plain':
                        content['plain_text'] = text
                    elif mime_type == 'text/html':
                        content['html'] = text
            
            # Handle nested parts
            if 'parts' in part:
                self._parse_message_parts(part['parts'], content)
            
            # Handle attachments
            if 'filename' in part and part['filename']:
                attachment = {
                    'filename': part['filename'],
                    'mime_type': part['mimeType'],
                    'size': part.get('body', {}).get('size', 0)
                }
                content.setdefault('attachments', []).append(attachment)

    def get_detailed_message(self, message_id: str) -> Dict[str, Any]:
        """Get detailed message content including all parts and metadata."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = {}
            for header in message['payload']['headers']:
                name = header['name'].lower()
                headers[name] = header['value']

            # Initialize content dictionary
            content = {
                'id': message['id'],
                'thread_id': message['threadId'],
                'label_ids': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'internal_date': message.get('internalDate'),
                'headers': headers,
                'plain_text': '',
                'html': '',
                'attachments': []
            }

            # Parse message parts
            if 'parts' in message['payload']:
                self._parse_message_parts(message['payload']['parts'], content)
            else:
                # Handle messages with no parts
                data = message['payload']['body'].get('data', '')
                if data:
                    text = base64.urlsafe_b64decode(data).decode()
                    if message['payload']['mimeType'] == 'text/plain':
                        content['plain_text'] = text
                    elif message['payload']['mimeType'] == 'text/html':
                        content['html'] = text

            return content

        except Exception as e:
            return None

    def dump_emails_by_labels(self, label_names: List[str], output_dir: str):
        """
        Dump emails for each specified label to separate JSON files.
        
        Args:
            label_names: List of label names to filter emails
            output_dir: Directory to save the JSON files
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for label_name in label_names:
                label = self.label_service.get_label_by_name(label_name)
                if not label:
                    continue

                label_id = label['id']
                query = f'label:{label_name}'

                messages = self.message_service.list_messages(query=query)
                emails = []

                for message in messages:
                    email_data = self.get_detailed_message(message['id'])
                    if email_data:
                        email_data['label_name'] = label_name
                        email_data['label_id'] = label_id
                        emails.append(email_data)

                if emails:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{label_name.replace('/', '_')}_{timestamp}.json"
                    file_path = output_path / filename
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(emails, f, ensure_ascii=False, indent=2)
                else:
                    pass

            return str(output_path)

        except Exception as e:
            return None

    def dump_emails_by_date_range(self, start_date: str, end_date: str, output_dir: str, overwrite: bool = False, verbose: bool = False) -> List[str]:
        """
        Dump emails within a specified date range to JSON files.
        
        Args:
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            output_dir: Base directory to save the JSON files
            overwrite: Whether to overwrite existing files
            verbose: Whether to enable verbose logging
            
        Returns:
            List of created file paths
        """
        try:
            # Convert dates to Gmail query format
            query = f'after:{start_date} before:{end_date}'
            if verbose:
                print(f"Fetching emails with query: {query}")

            messages = self.message_service.list_messages(query=query)
            created_files = []

            for message in messages:
                email_data = self.get_detailed_message(message['id'])
                if not email_data:
                    if verbose:
                        print(f"Failed to fetch email {message['id']}")
                    continue

                # Extract date from internalDate (Unix timestamp in milliseconds)
                timestamp = int(email_data['internal_date']) / 1000
                email_date = datetime.datetime.fromtimestamp(timestamp)
                
                # Create directory structure YYYY/MM/DD
                date_dir = os.path.join(
                    output_dir,
                    str(email_date.year),
                    str(email_date.month).zfill(2),
                    str(email_date.day).zfill(2)
                )
                os.makedirs(date_dir, exist_ok=True)

                # Save email to JSON file
                file_path = os.path.join(date_dir, f"{email_data['id']}.json")
                
                if os.path.exists(file_path) and not overwrite:
                    if verbose:
                        print(f"Skipping existing file: {file_path}")
                    continue

                if verbose:
                    print(f"Saving email to: {file_path}")

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(email_data, f, ensure_ascii=False, indent=2)
                created_files.append(file_path)

            return created_files

        except Exception as e:
            print(f"Error dumping emails: {str(e)}")
            print("Stack trace:")
            print(traceback.format_exc())
            return []
