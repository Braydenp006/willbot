import os
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()
SOURCE = os.environ["SOURCE"]

# Reads SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET from the environment.
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-modify-playback-state",
))

def pause(_):
    sp.pause_playback()

def play(query):
    title, _, artist = query.partition("|")
    title, artist = title.strip(), artist.strip()
    q = f"track:{title} artist:{artist}" if artist else title
    tracks = sp.search(q=q, type="track", limit=1)["tracks"]["items"]
    if not tracks and artist:  # filtered search found nothing; try plain words
        tracks = sp.search(q=f"{title} {artist}", type="track", limit=1)["tracks"]["items"]
    if not tracks:
        return None
    track = tracks[0]
    device = next((d for d in sp.devices()["devices"] if d["name"] == SOURCE), None)
    if device is None:
        raise RuntimeError(f"Spotify device {SOURCE!r} not found, is spotifyd running?")
    sp.start_playback(device_id=device["id"], uris=[track["uri"]])
    return f"{track['name']} by {track['artists'][0]['name']}"

if __name__ == "__main__":
    print(play(" ".join(sys.argv[1:])) or "No match")
