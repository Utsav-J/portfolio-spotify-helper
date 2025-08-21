import os
from typing import Dict, List
from dotenv     import load_dotenv

load_dotenv()

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Warning: Firebase not available. Install with: pip install firebase-admin")


class FirestoreManager:
    """Manages Firestore operations for storing Spotify track data"""
    
    def __init__(self, collection_name: str = "spotify"):
        self.collection_name = collection_name
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        if not FIREBASE_AVAILABLE:
            print("❌ Firebase not available. Install with: pip install firebase-admin")
            return
        
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try to load service account key from environment or default path
                service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                    print("✓ Firebase initialized with service account")
                else:
                    # Try to use default credentials (for Google Cloud environments)
                    firebase_admin.initialize_app()
                    print("✓ Firebase initialized with default credentials")
            
            self.db = firestore.client()
            print("✓ Firestore client initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize Firebase: {e}")
            self.db = None
    
    def add_track_document(self, track_id: str, track_name: str, track_artists: str, track_url: str) -> bool:
        """
        Add a track document to the spotify collection
        
        Args:
            track_id: Spotify track ID
            track_name: Name of the track
            track_artists: Artist(s) of the track
            track_url: Spotify URL of the track
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            print(f"❌ Firestore not available. Skipping track: {track_name}")
            return False
        
        try:
            # Create document data
            track_data = {
                "track_name": track_name,
                "track_artists": track_artists,
                "track_url": track_url,
                "added_at": firestore.SERVER_TIMESTAMP
            }
            
            # Add document to Firestore
            doc_ref = self.db.collection(self.collection_name).document(track_id)
            doc_ref.set(track_data)
            
            print(f"✓ Added track to Firestore: {track_name} - {track_artists}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add track to Firestore: {track_name} - Error: {e}")
            return False
    
    def check_track_exists(self, track_id: str) -> bool:
        """
        Check if a track already exists in Firestore
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            True if track exists, False otherwise
        """
        if not self.db:
            return False
        
        try:
            doc_ref = self.db.collection(self.collection_name).document(track_id)
            doc = doc_ref.get()
            return doc.exists
        except Exception as e:
            print(f"❌ Error checking track existence: {e}")
            return False
    
    def batch_add_tracks(self, tracks_data: List[Dict], skip_existing: bool = True) -> Dict[str, int]:
        """
        Add multiple tracks in a batch operation
        
        Args:
            tracks_data: List of track dictionaries with required fields
            skip_existing: Whether to skip tracks that already exist
            
        Returns:
            Dictionary with success, failure, and skipped counts
        """
        if not self.db:
            print("❌ Firestore not available. Skipping batch operation.")
            return {"success": 0, "failed": 0, "skipped": 0}
        
        try:
            batch = self.db.batch()
            success_count = 0
            failed_count = 0
            skipped_count = 0
            
            for track_data in tracks_data:
                try:
                    track_id = track_data.get("track_id")
                    if not track_id:
                        print(f"❌ Skipping track without ID: {track_data.get('track_name', 'Unknown')}")
                        failed_count += 1
                        continue
                    
                    # Check if track already exists
                    if skip_existing and self.check_track_exists(track_id):
                        print(f"⏭️  Skipping existing track: {track_data.get('track_name', 'Unknown')}")
                        skipped_count += 1
                        continue
                    
                    # Create document data
                    doc_data = {
                        "track_name": track_data.get("track_name", ""),
                        "track_artists": track_data.get("track_artists", ""),
                        "track_url": track_data.get("track_url", ""),
                        "added_at": firestore.SERVER_TIMESTAMP
                    }
                    
                    # Add to batch
                    doc_ref = self.db.collection(self.collection_name).document(track_id)
                    batch.set(doc_ref, doc_data)
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Error preparing track for batch: {e}")
                    failed_count += 1
            
            # Commit the batch
            if success_count > 0:
                batch.commit()
                print(f"✓ Batch operation completed: {success_count} tracks added, {failed_count} failed, {skipped_count} skipped")
            
            return {"success": success_count, "failed": failed_count, "skipped": skipped_count}
            
        except Exception as e:
            print(f"❌ Batch operation failed: {e}")
            return {"success": 0, "failed": len(tracks_data), "skipped": 0}
    
    def clear_all_tracks(self) -> Dict[str, int]:
        """
        Clear all documents from the spotify collection
        
        Returns:
            Dictionary with deletion count and status
        """
        if not self.db:
            print("❌ Firestore not available. Cannot clear collection.")
            return {"deleted": 0, "status": "failed", "error": "Firestore not available"}
        
        try:
            print(f"🗑️  Clearing all documents from '{self.collection_name}' collection...")
            
            # Get all documents in the collection
            docs = self.db.collection(self.collection_name).stream()
            doc_count = 0
            batch = self.db.batch()
            
            # Prepare batch delete
            for doc in docs:
                batch.delete(doc.reference)
                doc_count += 1
            
            if doc_count > 0:
                # Commit the batch deletion
                batch.commit()
                print(f"✅ Successfully deleted {doc_count} documents from '{self.collection_name}' collection")
                return {"deleted": doc_count, "status": "success"}
            else:
                print(f"ℹ️  No documents found in '{self.collection_name}' collection")
                return {"deleted": 0, "status": "success", "message": "Collection was already empty"}
                
        except Exception as e:
            error_msg = f"Failed to clear collection: {e}"
            print(f"❌ {error_msg}")
            return {"deleted": 0, "status": "failed", "error": error_msg}
    
    def get_collection_stats(self) -> Dict[str, any]:
        """
        Get statistics about the spotify collection
        
        Returns:
            Dictionary with collection statistics
        """
        if not self.db:
            return {"status": "failed", "error": "Firestore not available"}
        
        try:
            docs = list(self.db.collection(self.collection_name).stream())
            doc_count = len(docs)
            
            # Get some sample document IDs
            sample_ids = [doc.id for doc in docs[:5]] if docs else []
            
            return {
                "status": "success",
                "total_documents": doc_count,
                "sample_document_ids": sample_ids,
                "collection_name": self.collection_name
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}


def clear_spotify_collection():
    """
    Standalone function to clear all documents from the spotify collection.
    This can be called independently without needing the full SpotifyPlaylistFetcher.
    """
    print("🧹 Standalone Firestore Collection Cleaner")
    print("=" * 50)
    
    # Initialize FirestoreManager independently
    firestore_manager = FirestoreManager()
    
    # Show current collection stats
    print("\n📊 Current collection status:")
    stats = firestore_manager.get_collection_stats()
    if stats["status"] == "success":
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Total documents: {stats['total_documents']}")
        if stats['sample_document_ids']:
            print(f"   Sample IDs: {', '.join(stats['sample_document_ids'])}")
    else:
        print(f"   Error: {stats['error']}")
        return
    
    # Ask for confirmation
    if stats["total_documents"] > 0:
        print(f"\n⚠️  WARNING: This will delete {stats['total_documents']} documents!")
        confirm = input("Type 'DELETE' to confirm: ")
        
        if confirm == "DELETE":
            result = firestore_manager.clear_all_tracks()
            if result["status"] == "success":
                print(f"\n✅ Collection cleared successfully!")
                print(f"   Documents deleted: {result['deleted']}")
            else:
                print(f"\n❌ Failed to clear collection: {result.get('error', 'Unknown error')}")
        else:
            print("❌ Operation cancelled by user")
    else:
        print("\nℹ️  Collection is already empty")


if __name__ == "__main__":
    clear_spotify_collection()