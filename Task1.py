import os
import random
from youtube_dl import YoutubeDL
from pydub import AudioSegment
from supabase import create_client, Client

# Supabase setup
url: str = "YOUR_SUPABASE_URL"
key: str = "YOUR_SUPABASE_KEY"
supabase: Client = create_client(url, key)

# YouTube URLs to process
youtube_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    # Add more URLs as needed
]

def download_audio(url: str) -> str:
    """Download audio from YouTube video."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(id)s.%(ext)s',
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"{info['id']}.mp3"

def create_clip(audio_file: str, start: int, duration: int) -> str:
    """Create a clip from the audio file."""
    audio = AudioSegment.from_mp3(audio_file)
    clip = audio[start:start+duration]
    clip_name = f"clip_{random.randint(1000, 9999)}.mp3"
    clip.export(clip_name, format="mp3")
    return clip_name

def upload_to_supabase(file_path: str, bucket_name: str) -> str:
    """Upload file to Supabase storage and return public URL."""
    with open(file_path, "rb") as file:
        response = supabase.storage.from_(bucket_name).upload(file.name, file)
    return supabase.storage.from_(bucket_name).get_public_url(file.name)

def process_video(url: str, bucket_name: str):
    """Process a single video: download, create clips, and upload."""
    print(f"Processing video: {url}")
    audio_file = download_audio(url)
    
    for i in range(3):  # Create 3 clips per video
        start = random.randint(0, 300) * 1000  # Random start time (0-300 seconds)
        duration = random.randint(10, 30) * 1000  # Random duration (10-30 seconds)
        
        clip_file = create_clip(audio_file, start, duration)
        public_url = upload_to_supabase(clip_file, bucket_name)
        
        print(f"Clip {i+1} uploaded: {public_url}")
        
        os.remove(clip_file)  # Clean up the clip file
    
    os.remove(audio_file)  # Clean up the original audio file

def main():
    bucket_name = "audio-clips"
    
    for url in youtube_urls:
        process_video(url, bucket_name)

if __name__ == "__main__":
    main()