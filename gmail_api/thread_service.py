from typing import List, Dict, Any, Optional

class ThreadService:
    def __init__(self, service):
        """Initialize Thread service with Gmail API service."""
        self.service = service

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific email thread and all its messages.
        
        Args:
            thread_id: ID of the thread to retrieve
            
        Returns:
            Thread object with messages if successful, None otherwise
        """
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            return thread
        except Exception as e:
            print(f"Error retrieving thread: {str(e)}")
            return None

    def list_threads(self, query: str = '', max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List email threads matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum number of threads to retrieve
            
        Returns:
            List of thread objects
        """
        try:
            threads = self.service.users().threads().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            return threads.get('threads', [])
        except Exception as e:
            print(f"Error listing threads: {str(e)}")
            return []

    def modify_thread(self, thread_id: str, add_labels: List[str] = None, 
                     remove_labels: List[str] = None) -> bool:
        """
        Modify labels for all messages in a thread.
        
        Args:
            thread_id: ID of the thread to modify
            add_labels: List of label IDs to add
            remove_labels: List of label IDs to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            if body:
                self.service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body=body
                ).execute()
            return True
        except Exception as e:
            print(f"Error modifying thread: {str(e)}")
            return False

    def trash_thread(self, thread_id: str) -> bool:
        """
        Move a thread to trash.
        
        Args:
            thread_id: ID of the thread to trash
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().threads().trash(
                userId='me',
                id=thread_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error moving thread to trash: {str(e)}")
            return False

    def untrash_thread(self, thread_id: str) -> bool:
        """
        Restore a thread from trash.
        
        Args:
            thread_id: ID of the thread to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().threads().untrash(
                userId='me',
                id=thread_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error restoring thread from trash: {str(e)}")
            return False
