import os
import numpy as np
from yt_dlp import YoutubeDL
from pydub import AudioSegment
from supabase import create_client, Client
import whisper
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Supabase setup
url: str = "supa URL"
key: str = "Key"
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
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': '%(id)s.%(ext)s',
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"{info['id']}.wav"

def segment_audio(audio_file: str, segment_length: int = 10000) -> list:
    """Segment audio file into chunks."""
    audio = AudioSegment.from_wav(audio_file)
    return [audio[i:i+segment_length] for i in range(0, len(audio), segment_length)]

def analyze_audio_energy(segment: AudioSegment) -> float:
    """Calculate the energy (loudness) of an audio segment."""
    return segment.rms

def transcribe_audio(audio_file: str) -> list:
    """Transcribe entire audio file using Whisper and return list of transcriptions."""
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return [segment['text'] for segment in result['segments']]

def calculate_relevance_score(transcript: str, keywords: list) -> float:
    """Calculate relevance score based on keyword presence."""
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([transcript] + keywords)
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    return np.mean(cosine_similarities)

def select_best_segments(segments: list, transcripts: list, energies: list, relevance_scores: list, num_clips: int = 3) -> list:
    """Select the best segments based on energy and relevance."""
    combined_scores = [e * r for e, r in zip(energies, relevance_scores)]
    best_indices = sorted(range(len(combined_scores)), key=lambda i: combined_scores[i], reverse=True)[:num_clips]
    return [segments[i] for i in best_indices]

def create_clip(segment: AudioSegment, index: int) -> str:
    """Create a clip from an audio segment."""
    clip_name = f"clip_{index}.wav"
    segment.export(clip_name, format="wav")
    return clip_name

def upload_to_supabase(file_path: str, bucket_name: str) -> str:
    """Upload file to Supabase storage and return public URL."""
    with open(file_path, "rb") as file:
        response = supabase.storage.from_(bucket_name).upload(file.name, file)
    return supabase.storage.from_(bucket_name).get_public_url(file.name)

def process_video(url: str, bucket_name: str, keywords: list):
    """Process a single video: download, analyze, create clips, and upload."""
    print(f"Processing video: {url}")
    audio_file = download_audio(url)
    segments = segment_audio(audio_file)
    
    energies = [analyze_audio_energy(segment) for segment in segments]
    transcripts = transcribe_audio(audio_file)
    
    # Ensure we have the same number of transcripts as segments
    transcripts = transcripts[:len(segments)]
    if len(transcripts) < len(segments):
        transcripts.extend([''] * (len(segments) - len(transcripts)))
    
    relevance_scores = [calculate_relevance_score(transcript, keywords) for transcript in transcripts]
    
    best_segments = select_best_segments(segments, transcripts, energies, relevance_scores)
    
    for i, segment in enumerate(best_segments):
        clip_file = create_clip(segment, i)
        public_url = upload_to_supabase(clip_file, bucket_name)
        
        print(f"Clip {i+1} uploaded: {public_url}")
        
        os.remove(clip_file)  # Clean up the clip file
    
    os.remove(audio_file)  # Clean up the original audio file

def main():
    bucket_name = "audio-clips"
    keywords = ["important", "key point", "conclusion", "in summary","artificial intelligence", "machine learning", "blockchain", "cybersecurity", "innovation", "breakthrough", "revolutionary"]  
    
    for url in youtube_urls:
        process_video(url, bucket_name, keywords)

if __name__ == "__main__":
    main()