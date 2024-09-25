import yt_dlp
import os
import subprocess
import supabase
import uuid
import spacy
import openai

# Initialize OpenAI API key
openai.api_key = "your_openai_api_key"

# Load spaCy's English model
nlp = spacy.load("en_core_web_sm")

# Configure Supabase
url = "url"
key = "your_supabase_key"
supabase_client = supabase.create_client(url, key)

def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'tmp/%(id)s.%(ext)s',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        return f"tmp/{info_dict['id']}.mp4"

def process_video(video_path):
    wav_path = f"{video_path[:-4]}.wav"
    command = ['ffmpeg', '-i', video_path, wav_path]
    subprocess.run(command, check=True)
    return wav_path

def transcribe_audio(wav_path):
    """
    Transcribe audio using OpenAI GPT API.
    The function reads the audio file and sends it to the OpenAI API for transcription.
    """
    try:
        with open(wav_path, 'rb') as audio_file:
            # Use OpenAI's API to transcribe audio
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            return transcript["text"]  # Extract text from the response
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def score_segment(segment):
    keywords = ["important", "valuable", "insightful"]
    score = sum(1 for word in keywords if word in segment.lower())
    return score

def find_valuable_segments(transcript):
    # Process the transcript with spaCy
    doc = nlp(transcript)
    scored_segments = []

    # Split transcript into sentences
    for sentence in doc.sents:
        score = score_segment(sentence.text)
        if score > 0:  # Only keep segments with a score greater than zero
            scored_segments.append((sentence.text, score))

    # Sort segments by score in descending order
    scored_segments.sort(key=lambda x: x[1], reverse=True)
    return scored_segments

def upload_to_supabase(file_path):
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as file:
        supabase_client.storage.from_("videos").upload(file_name, file)

def upload_metadata_to_supabase(clip_data):
    supabase_client.from_("videos").insert(clip_data).execute()

def main(video_urls):
    for url in video_urls:
        video_path = download_video(url)
        wav_path = process_video(video_path)
        transcript = transcribe_audio(wav_path)

        # If transcription fails, skip to the next video
        if not transcript:
            continue

        # Find valuable segments from the transcript
        valuable_segments = find_valuable_segments(transcript)

        for segment, score in valuable_segments:
            print(f"Segment: {segment}, Score: {score}")
            # Create clip data for Supabase
            clip_data = {
                "id": str(uuid.uuid4()),
                "title": "Clip Title",
                "tags": ["important", "insightful"],  # I need to work on tags
                "transcript": segment,
                "url": f"url_to_the_clip_{score}"  # Placeholder for the actual clip URL
            }
            upload_metadata_to_supabase(clip_data)

if __name__ == "__main__":
    test_urls = ["https://www.youtube.com/watch?v=bc6uFV9CJGg", "https://www.youtube.com/watch?v=6u4JVz7iQTY"]
    main(test_urls)
