
import base64
import re
import time
from typing import Dict, List
import requests
from firestore_manager import FirestoreManager
from token_keystore import TokenKeystore
from dotenv     import load_dotenv

load_dotenv()

class SpotifyPlaylistFetcher:
    def __init__(self, client_id: str, client_secret: str, keystore_path: str = ".spotify_keystore.json"):
        """
        Initialize the Spotify API client
        
        Args:
            client_id: Your Spotify app client ID
            client_secret: Your Spotify app client secret
            keystore_path: Path to the keystore file
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://api.spotify.com/v1"
        self.keystore = TokenKeystore(keystore_path)
        self.firestore_manager = FirestoreManager()
        
        # Try to load existing valid token
        self._load_cached_token()
    
    def _load_cached_token(self):
        """Load cached token if it's valid"""
        cached_token = self.keystore.get_valid_token()
        if cached_token:
            self.access_token = cached_token
            print("✓ Loaded cached access token")
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get access token using client credentials flow or from cache
        
        Args:
            force_refresh: Force refresh even if cached token is valid
            
        Returns:
            Access token string
        """
        # Check if we have a valid cached token (unless forcing refresh)
        if not force_refresh and self.keystore.is_token_valid():
            self.access_token = self.keystore.get_valid_token()
            return self.access_token
        
        print("Fetching new access token...")
        
        # Encode client credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Prepare headers and data for token request
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        # Make request to get token
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            
            # Store token in keystore
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self.keystore.store_token(self.access_token, expires_in)
            
            print("✓ New access token obtained and cached")
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")
    
    def ensure_valid_token(self) -> str:
        """
        Ensure we have a valid access token, fetching new one if needed
        
        Returns:
            Valid access token string
        """
        if not self.access_token or not self.keystore.is_token_valid():
            return self.get_access_token()
        return self.access_token
    
    def show_keystore_status(self):
        """Display current keystore status"""
        token_info = self.keystore.get_token_info()
        print("\n=== Keystore Status ===")
        print(f"Status: {token_info['status']}")
        
        if token_info['status'] != "no_token":
            print(f"Token Preview: {token_info['token_preview']}")
            print(f"Created: {time.ctime(token_info['created_at'])}")
            print(f"Expires: {time.ctime(token_info['expires_at'])}")
            print(f"Time until expiry: {token_info['time_until_expiry']} seconds")
        print("=" * 20)
    
    def clear_keystore(self):
        """Clear the keystore and force new token fetch"""
        self.keystore.clear_token()
        self.access_token = None
        print("✓ Keystore cleared")
    
    def extract_playlist_id(self, playlist_url: str) -> str:
        """
        Extract playlist ID from Spotify URL
        
        Args:
            playlist_url: Spotify playlist URL
            
        Returns:
            Playlist ID string
        """
        # Handle different URL formats
        patterns = [
            r'https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)',
            r'spotify:playlist:([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, playlist_url)
            if match:
                return match.group(1)
        
        raise ValueError("Invalid Spotify playlist URL format")
    
    def get_playlist_tracks(self, playlist_id: str, limit: int = 50) -> List[Dict]:
        """
        Get all tracks from a playlist
        
        Args:
            playlist_id: Spotify playlist ID
            limit: Number of tracks to fetch per request (max 50)
            
        Returns:
            List of track information dictionaries
        """
        # Ensure we have a valid token
        self.ensure_valid_token()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        all_tracks = []
        offset = 0
        
        while True:
            # Make request to get playlist items
            params = {
                "limit": limit,
                "offset": offset,
                "fields": "items(track(name,artists(name),external_urls,uri,id)),next,total"
            }
            
            response = requests.get(
                f"{self.base_url}/playlists/{playlist_id}/tracks",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get playlist tracks: {response.status_code} - {response.text}")
            
            data = response.json()
            tracks = data.get("items", [])
            
            # Filter out None tracks (can happen with removed tracks)
            valid_tracks = [item for item in tracks if item.get("track") is not None]
            all_tracks.extend(valid_tracks)
            
            # Check if there are more tracks to fetch
            if not data.get("next"):
                break
            
            offset += limit
        print(all_tracks)
        return all_tracks
    
    def print_track_urls(self, tracks: List[Dict]):
        """
        Print track URLs for all tracks
        
        Args:
            tracks: List of track items from playlist
        """
        print(f"\nFound {len(tracks)} tracks in the playlist:\n")
        print("-" * 80)
        
        for i, item in enumerate(tracks, 1):
            track = item.get("track")
            if track:
                track_name = track.get("name", "Unknown")
                artists = ", ".join([artist.get("name", "Unknown") for artist in track.get("artists", [])])
                track_url = track.get("external_urls", {}).get("spotify", "N/A")
                
                print(f"{i:3d}. {track_name} - {artists}")
                print(f"     URL: {track_url}")
                print()
    
    def fetch_and_print_playlist_tracks(self, playlist_url: str):
        """
        Main method to fetch and print all track URLs from a playlist
        
        Args:
            playlist_url: Spotify playlist URL
        """
        try:
            print("Checking access token...")
            # Token will be automatically fetched if needed
            self.ensure_valid_token()
            print("✓ Access token ready")
            
            print("Extracting playlist ID...")
            playlist_id = self.extract_playlist_id(playlist_url)
            print(f"✓ Playlist ID: {playlist_id}")
            
            print("Fetching playlist tracks...")
            trackList = self.get_playlist_tracks(playlist_id)
            
            print(f"✓ Fetched {len(trackList)} tracks")
            
            # Prepare tracks data for Firestore
            tracks_data = []
            print("\n📝 Processing tracks for Firestore...")
            
            for item in trackList:
                track = item.get("track")
                if track:
                    track_id = track.get("id")
                    track_name = track.get("name", "Unknown")
                    track_artists = ", ".join([artist.get("name", "Unknown") for artist in track.get("artists", [])])
                    track_url = track.get("external_urls", {}).get("spotify", "N/A")
                    
                    # Print track info
                    print(f"🎵 {track_name} - {track_artists} - {track_url}")
                    
                    # Prepare data for Firestore
                    if track_id:
                        tracks_data.append({
                            "track_id": track_id,
                            "track_name": track_name,
                            "track_artists": track_artists,
                            "track_url": track_url
                        })
                    else:
                        print(f"⚠️  Skipping track without ID: {track_name}")
            
            # Store tracks in Firestore
            if tracks_data:
                print(f"\n🔥 Storing {len(tracks_data)} tracks in Firestore...")
                result = self.firestore_manager.batch_add_tracks(tracks_data)
                print(f"✅ Firestore operation completed: {result['success']} tracks added, {result['failed']} failed")
            else:
                print("⚠️  No valid tracks to store in Firestore")
            
            # Also print formatted track list
            self.print_track_urls(trackList)
            
        except Exception as e:
            print(f"Error: {e}")
