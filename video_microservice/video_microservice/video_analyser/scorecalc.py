import speech_recognition as sr
from pydub import AudioSegment
from openai import OpenAI
import Levenshtein
import requests
import os
import numpy as np
import librosa
from sklearn.ensemble import RandomForestClassifier
from pathlib import Path
from joblib import load
import joblib
from pymongo import MongoClient
from bson import ObjectId

# Load the RandomForestClassifier model
clf = joblib.load('video_analyser/ML/model.joblib')

BASE_DIR = Path(__file__).resolve().parent.parent







# Function to extract MFCC features from audio file
def extract_features(audio_file, num_mfcc=13):
    try:
        # Load audio file
        y, sr = librosa.load(audio_file, sr=None)
        # Extract MFCC features
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=num_mfcc)
        # Return flattened MFCCs
        return np.mean(mfccs.T, axis=0)
    except Exception as e:
        print("Error encountered while parsing file:", audio_file)
        return None


def label(arr):
    if arr[0][1] >= 0.7:
        return "high"
    elif 0.5 < arr[0][1] < 0.7:
        return "medium"
    else:
        return "low"


def fluency_calculator(text):
    fluency_non = ['cant', 'wont', 'dont', 'Well', 'You know', 'Actually', 'like', 'so', 'um', 'ummm', 'umm', 'uhh', 'uh', 'aah', 'ah', 'ahh', 'ahhh', 'basically', 'maybe', 'not sure', 'i think', 'i feel', 'might', 'suppose']
    count = 0
    for i in fluency_non:
        if i in text:
            count += 1
    print(count)
    return count


def language_calculator(original_text, corrected_text):
    distance = Levenshtein.distance(original_text, corrected_text)
    accuracy = 100 - (distance / len(original_text) * 100)
    return accuracy

from pydub import AudioSegment

# Function to extract audio from video using Pydub
def extract_audio(video_path, audio_path):
    try:
        # Load video file
        video = AudioSegment.from_file(video_path, format="mp4")
        # Set audio parameters
        audio = video.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        # Export audio to WAV format
        audio.export(audio_path, format="wav")
        print("Audio extracted successfully.")
        return True
    except Exception as e:
        print("Error extracting audio:", e)
        return False



def download_sample_video(url, save_path):
    response = requests.get(url)
    with open(save_path, 'wb') as file:
        file.write(response.content)


def combined_score_calculator(talentId):
    print(BASE_DIR)
    try:
        client = MongoClient(
            "mongodb://uptime:Basketball10@134.122.18.134:27017/Highpo_prod_copy?authSource=admin&w=1&readPreference=primary&appname=MongoDB%20Compass&directConnection=true&ssl=false"
        )
        db = client["Highpo_prod_copy"]
        video_collection = db["talents"]
        talent_id_object = ObjectId(talentId)

        document = video_collection.find_one({"_id": talent_id_object}, {"_id": 1, "videoUrl": 1})
        print(document)
        sample_video_url = document.get("videoUrl", "")
        print("*****")
        video_path = os.path.join(BASE_DIR, 'video_analyser', 'assets', f'{talentId}.mp4')
        print(video_path)
        download_sample_video(sample_video_url, video_path)

        sound_dir = os.path.join(BASE_DIR, 'video_analyser', 'sound')
        audio_path = os.path.join(sound_dir, f'{talentId}.wav')
        print(video_path)

        if not os.path.exists(video_path):
            print(f"Error: Video file '{talentId}.mp4' not found.")
            return None

        if not extract_audio(video_path, audio_path):
            print("Failed to extract audio.")
            return None
        # Recognize speech in the audio
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_text = r.record(source)
        text = r.recognize_google(audio_text, language='en-US')
        print("Recognized Text:", text)

        # Call OpenAI API to correct the text
        client = OpenAI(api_key='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')
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You will be provided with statements, and your task is to convert them to standard English."},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=len(text),
            top_p=1
        )
        corrected_text = response.choices[0].message.content
        print("Corrected Text:", corrected_text)

        # Calculate language accuracy
        language_accuracy = language_calculator(text, corrected_text)
        print(f"Accuracy: {language_accuracy:.2f}%")

        # Calculate fluency score
        nonfluency_count = fluency_calculator(text)
        fluency_score = 100 - (nonfluency_count / len(text) * 150)
        fluency_score = max(fluency_score, 10)
        print(f"Fluency Score: {fluency_score:.2f}%")

        feature_array = extract_features(audio_path)

        feature_array_reshape = feature_array.reshape(1, -1)
        y_pred = clf.predict(feature_array_reshape)
        print(y_pred)

        confidence_score_range = clf.predict_proba(feature_array_reshape)
        
        confidence_label = label(confidence_score_range)


        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Deleted video: {video_path}")
        else:
            print(f"File not found: {video_path}")

        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"Deleted audio: {audio_path}")
        else:
            print(f"File not found: {audio_path}")

        

        return (language_accuracy, fluency_score,confidence_label)

    except Exception as e:
        print("Error:", e)
        return None


    