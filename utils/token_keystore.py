import json
from pathlib import Path
import time
from typing import Dict, Optional
from dotenv     import load_dotenv
load_dotenv()


class TokenKeystore:
    """Local keystore for storing and managing Spotify access tokens"""
    
    def __init__(self, keystore_path: str = ".spotify_keystore.json"):
        self.keystore_path = Path(keystore_path)
        self.token_data = self._load_keystore()
    
    def _load_keystore(self) -> Dict:
        """Load existing keystore or create new one"""
        if self.keystore_path.exists():
            try:
                with open(self.keystore_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If keystore is corrupted, start fresh
                return {}
        return {}
    
    def _save_keystore(self):
        """Save current keystore to file"""
        try:
            with open(self.keystore_path, 'w') as f:
                json.dump(self.token_data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save keystore: {e}")
    
    def store_token(self, access_token: str, expires_in: int):
        """Store access token with expiration time"""
        current_time = int(time.time())
        self.token_data = {
            "access_token": access_token,
            "expires_at": current_time + expires_in,
            "created_at": current_time
        }
        self._save_keystore()
    
    def get_valid_token(self) -> Optional[str]:
        """Get valid token if it exists and hasn't expired"""
        if not self.token_data:
            return None
        
        current_time = int(time.time())
        expires_at = self.token_data.get("expires_at", 0)
        
        # Check if token is expired (with 60 second buffer)
        if current_time >= (expires_at - 60):
            return None
        
        return self.token_data.get("access_token")
    
    def clear_token(self):
        """Clear stored token"""
        self.token_data = {}
        self._save_keystore()
    
    def is_token_valid(self) -> bool:
        """Check if stored token is still valid"""
        return self.get_valid_token() is not None
    
    def get_token_info(self) -> Dict:
        """Get information about the stored token"""
        if not self.token_data:
            return {"status": "no_token"}
        
        current_time = int(time.time())
        expires_at = self.token_data.get("expires_at", 0)
        created_at = self.token_data.get("created_at", 0)
        
        return {
            "status": "valid" if self.is_token_valid() else "expired",
            "created_at": created_at,
            "expires_at": expires_at,
            "time_until_expiry": max(0, expires_at - current_time),
            "token_preview": self.token_data.get("access_token", "")[:20] + "..." if self.token_data.get("access_token") else None
        }
