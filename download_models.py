import os
import requests

def download_file(url, local_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def main():
    base_url = "https://github.com/justadudewhohacks/face-api.js/raw/master/weights"
    models = [
        "tiny_face_detector_model-weights_manifest.json",
        "tiny_face_detector_model-shard1",
        "face_landmark_68_model-weights_manifest.json",
        "face_landmark_68_model-shard1",
        "face_recognition_model-weights_manifest.json",
        "face_recognition_model-shard1",
        "face_recognition_model-shard2"
    ]
    
    for model in models:
        url = f"{base_url}/{model}"
        local_path = os.path.join("static", "weights", model)
        print(f"Downloading {model}...")
        download_file(url, local_path)
    
    print("All models downloaded successfully!")

if __name__ == "__main__":
    main()
