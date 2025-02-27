import os
import base64
import logging

import requests
from pydub import AudioSegment


def get_wav_file_size(path: str) -> float:
    size_mb = os.path.getsize(path) / (1024 * 1024)  # Convert bytes to MB
    return size_mb

def convert_to_wav(input_filepath: str, output_filepath: str | None = None) -> str | None:
    if output_filepath == None: output_filepath = '.'.join(input_filepath.split('.')[:-1])+'.wav'
    try:
        audio = AudioSegment.from_file(input_filepath)
        audio.export(output_filepath, format="wav")
        os.remove(input_filepath)  # Remove the original file after conversion
        return output_filepath
    except Exception as e:
        logging.error(f"Error converting file to WAV: {e}")
        return None

def download_chunk_audio_file(conversation_id: int, chunk_id: int, file_extension: str,
                              root_dir: str, url: str,
                              access_token: str = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImYwMWJiMDhiLTE0ZWItNDkyZC1hN2ZkLTFlZWQ4OWVhNDUyYiIsInJvbGUiOiIyZWFiNjNlMC1mODczLTRjYTctYjMzYS1jYzIwNTcyNDQzYzEiLCJhcHBfYWNjZXNzIjp0cnVlLCJhZG1pbl9hY2Nlc3MiOnRydWUsInNlc3Npb24iOiJzM1p1UFprZnIzRmFiNW5JemhKNEVPb1VIRkZTQWZDcGw3NGlnemtMTmJreDVLU2tjRm1xdlpZXy1ybllhT2NpIiwiaWF0IjoxNzQwNjQzMTY0LCJleHAiOjE3NDA3Mjk1NjQsImlzcyI6ImRpcmVjdHVzIn0.LeJxy0VYy-EWsI19YxoviUZ-rG0PdC-GYJmRogV9CN0',
                              ) -> str | None:
    url = url.format(conversation_id = conversation_id,chunk_id = chunk_id)
    # Set headers
    headers = {"Accept": "*/*"}
    if access_token:
        headers["Cookie"] = f"directus_session_token={access_token}"
    # Send GET request
    response = requests.get(url, headers=headers)
    # Check response status
    if response.status_code == 200:
        # Ensure root directory exists
        os.makedirs(root_dir, exist_ok=True)
        # Generate filename with root directory
        filename = os.path.join(root_dir, f"{conversation_id}_{chunk_id}.{file_extension}")
        # Save file
        with open(filename, "wb") as file:
            file.write(response.content)
        if file_extension != 'wav':
            return convert_to_wav(filename)
        else:
            return filename
    else:
        logging.error(f"Failed to download file. Status Code: {response.status_code}, Response: {response.text}")
        return None

def split_wav_to_chunks(input_filepath: str, n_chunks: int, counter: int, output_filedir: str) -> list[str]:

    chunk_name = input_filepath.split('/')[-1].split('.')[0].split('_')[0] + "_" + str(counter)
    # Load the audio file
    audio = AudioSegment.from_wav(input_filepath)
    
    # Calculate chunk length
    chunk_length = len(audio) // n_chunks  # Duration in milliseconds
    output_files = []
    for i in range(n_chunks):
        chunk_output_filename = chunk_name + '-' + str(i) +'.wav'
        chunk_output_filepath = os.path.join(output_filedir,chunk_output_filename)
        start_time = i * chunk_length
        end_time = (i + 1) * chunk_length if i != n_chunks - 1 else len(audio)
        chunk = audio[start_time:end_time]
        # Export chunk
        chunk.export(chunk_output_filepath, format="wav")
        output_files.append(chunk_output_filepath)

    return output_files

def process_wav_files(audio_filepath_list: list[str], output_filepath: str, max_size_mb: float, counter: int = 0) -> list[str]:
    """
    Ensures all files are segmented close to max_size_mb.
    **** File might be a little larger than max limit 
    """
    output_filedir = os.path.dirname(output_filepath)
    combined = AudioSegment.empty()
    combined.export(output_filepath, format="wav")
    while len(audio_filepath_list)!=0:
        file = audio_filepath_list[0]
        try:
            audio = AudioSegment.from_wav(file)
        except Exception as e:
            logging.error(f"Error loading wav audio file: {e}")
            break
        input_file_size = get_wav_file_size(file)
        # If the file is larger -> break to n_sub_chunks
        if input_file_size>max_size_mb:
            combined += audio
            n_sub_chunks = int((input_file_size//max_size_mb)+1)
            split_wav_to_chunks(file, n_sub_chunks,
                                counter = counter,
                                output_filedir = output_filedir)
            audio_filepath_list = audio_filepath_list[1:]
            os.remove(output_filepath)
            break
        else:
            combined += audio
            if get_wav_file_size(output_filepath) <= max_size_mb:
                combined.export(output_filepath, format="wav")
                audio_filepath_list = audio_filepath_list[1:]
            else: break
    return audio_filepath_list

def wav_to_str(wav_file_path: str) -> str:
    with open(wav_file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")