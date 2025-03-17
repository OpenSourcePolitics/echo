import os
import base64
import logging
from io import BytesIO

from pydub import AudioSegment

from dembrane.s3 import get_stream_from_s3, get_file_size_from_s3_mb
from dembrane.directus import directus


def get_audio_file_size(path: str) -> float:
    size_mb = os.path.getsize(path) / (1024 * 1024)  # Convert bytes to MB
    return size_mb


def convert_to_wav(input_filepath: str, output_filepath: str | None = None) -> str | None:
    # TODO: Check if the file is already a WAV file

    if output_filepath == None:
        output_filepath = ".".join(input_filepath.split(".")[:-1]) + ".wav"
    try:
        audio = AudioSegment.from_file(input_filepath)
        audio.export(output_filepath, format="wav")
        os.remove(input_filepath)  # Remove the original file after conversion
        return output_filepath
    except Exception as e:
        logging.error(f"Error converting file to WAV: {e}")
        return None


def download_chunk_audio_file_as_wav(
    conversation_id: int,
    chunk_id: int,
    temp_dir: str,
) -> str | None:
    try:
        chunk_response = directus.get_items(
            "conversation_chunk",
            {
                "query": {
                "filter": {
                    "id": {"_eq": chunk_id}
                }
                }
            },
        )

        if len(chunk_response) == 0:
            logging.error(
                f"Chunk not found for conversation_id: {conversation_id}, chunk_id: {chunk_id}"
            )
            return None

        chunk_data = chunk_response[0]
        original_audio_path = chunk_data["path"]

        file_extension = original_audio_path.split(".")[-1]
        temp_audio_path = os.path.join(temp_dir, f"{conversation_id}_{chunk_id}.{file_extension}")

        with open(original_audio_path, "rb") as src_file:
            with open(temp_audio_path, "wb") as dst_file:
                dst_file.write(src_file.read())

        if file_extension.lower() != "wav":
            return convert_to_wav(temp_audio_path)
        else:
            return temp_audio_path

    except Exception as e:
        logging.error(f"Failed to process audio file: {e}")
        return None


def split_wav_to_chunks(
    input_filepath: str, n_chunks: int, counter: int, output_filedir: str
) -> list[str]:
    chunk_name = input_filepath.split("/")[-1].split(".")[0].split("_")[0] + "_" + str(counter)
    # Load the audio file
    audio = AudioSegment.from_wav(input_filepath)

    # Calculate chunk length
    chunk_length = len(audio) // n_chunks  # Duration in milliseconds
    output_files = []
    for i in range(n_chunks):
        chunk_output_filename = chunk_name + "-" + str(i) + ".wav"
        chunk_output_filepath = os.path.join(output_filedir, chunk_output_filename)
        start_time = i * chunk_length
        end_time = (i + 1) * chunk_length if i != n_chunks - 1 else len(audio)
        chunk = audio[start_time:end_time]
        # Export chunk
        chunk.export(chunk_output_filepath, format="wav")
        output_files.append(chunk_output_filepath)

    return output_files


def process_wav_files(
    audio_filepath_list: list[str], output_filepath: str, max_size_mb: float, counter: int = 0
) -> list[str]:
    """
    Ensures all files are segmented close to max_size_mb.
    **** File might be a little larger than max limit
    """
    output_filedir = os.path.dirname(output_filepath)
    combined = AudioSegment.empty()
    combined.export(output_filepath, format="wav")
    while len(audio_filepath_list) != 0:
        file = audio_filepath_list[0]
        try:
            audio = AudioSegment.from_wav(file)
        except Exception as e:
            logging.error(f"Error loading wav audio file: {e}")
            break
        input_file_size = get_audio_file_size(file)
        # If the file is larger -> break to n_sub_chunks
        if input_file_size > max_size_mb:
            combined += audio
            n_sub_chunks = int((input_file_size // max_size_mb) + 1)
            split_wav_to_chunks(file, n_sub_chunks, counter=counter, output_filedir=output_filedir)
            audio_filepath_list = audio_filepath_list[1:]
            os.remove(output_filepath)
            break
        else:
            combined += audio
            if get_audio_file_size(output_filepath) <= max_size_mb:
                combined.export(output_filepath, format="wav")
                audio_filepath_list = audio_filepath_list[1:]
            else:
                break
    return audio_filepath_list

def wav_to_str(wav_file_path: str) -> str:
    with open(wav_file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")
    




def split_ogg_to_chunks(
    audio: bytes, conversation_id: str, 
    n_chunks: int, counter: int, output_filedir: str
) -> list[str]:
    # chunk_name = input_filepath.split("/")[-1].split(".")[0].split("_")[0] + "_" + str(counter)
    # # Load the audio file
    # audio = AudioSegment.from_ogg(input_filepath)

    # Calculate chunk length
    segment_name = conversation_id + "_" + str(counter)
    chunk_length = len(audio) // n_chunks  # Duration in milliseconds
    output_files = []
    for i in range(n_chunks):
        chunk_output_filename = segment_name + "-" + str(i) + ".wav"
        chunk_output_filepath = os.path.join(output_filedir, chunk_output_filename)
        start_time = i * chunk_length
        end_time = (i + 1) * chunk_length if i != n_chunks - 1 else len(audio)
        chunk = audio[start_time:end_time]
        # Export chunk
        chunk.export(chunk_output_filepath, format="wav") # type: ignore
        output_files.append(chunk_output_filepath)

    return output_files

def process_ogg_files(
    audio_filepath_list: list[str], output_filepath: str, 
    max_size_mb: float, conversation_id: str , counter: int, 
) -> list[str]:
    """
    Ensures all files are segmented close to max_size_mb.
    **** File might be a little larger than max limit
    """
    output_filedir = os.path.dirname(output_filepath)
    combined = AudioSegment.empty()
    combined.export(output_filepath, format="wav")
    while len(audio_filepath_list) != 0:
        audio_file_uri = audio_filepath_list[0]
        try:
            audio_stream = get_stream_from_s3(audio_file_uri)
            audio = AudioSegment.from_file(BytesIO(audio_stream.read()), format="ogg")
        except Exception as e:
            logging.error(f"Error loading ogg audio file: {e}")
            break
        input_file_size = get_file_size_from_s3_mb(audio_file_uri)
        # If the file is larger -> break to n_sub_chunks
        if input_file_size > max_size_mb:
            combined += audio
            n_sub_chunks = int((input_file_size // max_size_mb) + 1)
            split_ogg_to_chunks(audio, conversation_id, 
                                n_sub_chunks, 
                                counter, 
                                output_filedir)
            audio_filepath_list = audio_filepath_list[1:]
            os.remove(output_filepath)
            break
        else:
            combined += audio
            if get_audio_file_size(output_filepath) <= max_size_mb:
                combined.export(output_filepath, format="wav")
                audio_filepath_list = audio_filepath_list[1:]
            else:
                break
    return audio_filepath_list

def ogg_to_str(ogg_file_path: str) -> str:
    with open(ogg_file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")
