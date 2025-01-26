from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build

class LabelService:
    def __init__(self, service):
        """Initialize Label service with Gmail API service."""
        self.service = service

    def list_labels(self) -> List[Dict[str, Any]]:
        """
        List all labels in the user's mailbox.
        
        Returns:
            List of label objects containing id, name, and other metadata
        """
        try:
            results = self.service.users().labels().list(userId='me').execute()
            return results.get('labels', [])
        except Exception as e:
            print(f"Error listing labels: {str(e)}")
            return []

    def get_label_by_name(self, label_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a label by its name.
        
        Args:
            label_name: Name of the label to find
            
        Returns:
            Label object if found, None otherwise
        """
        try:
            labels = self.list_labels()
            # Try exact match first
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label
            
            # Try partial match (ignoring parent labels)
            label_parts = label_name.split('/')
            search_name = label_parts[-1].lower()
            
            for label in labels:
                label_name_parts = label['name'].split('/')
                if label_name_parts[-1].lower() == search_name:
                    return label
            
            return None
        except Exception as e:
            print(f"Error getting label by name: {str(e)}")
            return None

    def delete_label(self, label_id: str) -> bool:
        """
        Delete a label from Gmail.
        
        Args:
            label_id: ID of the label to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().labels().delete(userId='me', id=label_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting label: {str(e)}")
            return False

    def update_label(self, label_id: str, new_name: str, 
                    label_list_visibility: str = 'labelShow',
                    message_list_visibility: str = 'show') -> Optional[Dict[str, Any]]:
        """
        Update a label's properties.
        
        Args:
            label_id: ID of the label to update
            new_name: New name for the label
            label_list_visibility: Visibility in label list ('labelShow', 'labelHide', 'labelShowIfUnread')
            message_list_visibility: Visibility in message list ('show', 'hide')
            
        Returns:
            Updated label object if successful, None otherwise
        """
        try:
            label_object = {
                'name': new_name,
                'labelListVisibility': label_list_visibility,
                'messageListVisibility': message_list_visibility
            }
            
            updated_label = self.service.users().labels().patch(
                userId='me',
                id=label_id,
                body=label_object
            ).execute()
            
            return updated_label
        except Exception as e:
            print(f"Error updating label: {str(e)}")
            return None

    def create_label(self, label_name: str) -> Optional[str]:
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
