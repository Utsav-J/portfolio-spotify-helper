import os
from dotenv     import load_dotenv

from utils.spotify_playlist_fetcher import SpotifyPlaylistFetcher

load_dotenv()

def main():
    """
    Main function to run the program
    """
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    
    print("Enter the playlist URL:")
    PLAYLIST_URL = input()
    
    fetcher = SpotifyPlaylistFetcher(CLIENT_ID, CLIENT_SECRET)
    
    fetcher.show_keystore_status()
    
    fetcher.fetch_and_print_playlist_tracks(PLAYLIST_URL)
    
    fetcher.show_keystore_status()
    
    print("\n" + "="*50)
    print("Demonstrating token reuse...")
    print("="*50)
    
    fetcher.ensure_valid_token()
    
    fetcher.show_keystore_status()

if __name__ == "__main__":
    main()
