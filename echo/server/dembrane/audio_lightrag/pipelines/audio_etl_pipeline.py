import os

import yaml

from dembrane.audio_lightrag.utils.audio_utils import process_wav_files, download_chunk_audio_file
from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker


class AudioETLPipeline:
    def __init__(self, process_tracker: ProcessTracker, 
                 config_path: str = "server/dembrane/audio_lightrag/configs/audio_etl_pipeline_config.yaml") -> None:
        """
        Initialize the AudioETLPipeline.

        Args:
        - process_tracker (ProcessTracker): Instance to track the process.
        - config_path (str): Path to the configuration file.

        Returns:
        - None
        """
        self.process_tracker = process_tracker
        self.process_tracker_df = process_tracker()
        self.config = self.load_config(config_path)
        self.download_root_dir = self.config['download_root_dir']
        self.segment_root_dir = self.config['segment_root_dir']
        self.audio_url = self.config['audio_url']
        self.max_size_mb = self.config['max_audio_file_size_mb']
        
    def load_config(self, config_path: str) -> dict:
        """Load the configuration file.

        Args:
        - config_path (str): Path to the configuration file.

        Returns:
        - dict: Loaded configuration as a dictionary.
        """
        with open(config_path, "r") as file:
            return yaml.safe_load(file)


    def extract(self) -> None:
        # Get unique project and conversation IDs
        zip_unique = list(set(zip(self.process_tracker_df.project_id, 
                                  self.process_tracker_df.conversation_id)))

        for project_id, conversation_id in zip_unique:
            # Get unique chunk IDs for each project and conversation
            chunk_li = self.process_tracker_df.loc[
                (self.process_tracker_df.project_id == project_id) & 
                (self.process_tracker_df.conversation_id == conversation_id)
            ].chunk_id.unique()

            for chunk_id in chunk_li:
                file_extension = self.process_tracker()[self.process_tracker().chunk_id == chunk_id].format.unique()[0]

                # Download audio file for each chunk
                download_file_path = download_chunk_audio_file(conversation_id, chunk_id, 
                                                               file_extension, self.download_root_dir,
                                                               self.audio_url)
                if file_extension == 'mp4' : pass # TODO: implement mp4 to wav

                # Update process tracker with download status
                if download_file_path is not None:
                    self.process_tracker.update_download_status(conversation_id, chunk_id, 'pass')
                else:
                    self.process_tracker.update_download_status(conversation_id, chunk_id, 'fail')

    def transform(self) -> None:
        downloaded_process_tracker_df = self.process_tracker_df[
            (self.process_tracker_df.download_status == 'pass') &
            (self.process_tracker_df.segment.isna() == True)]	
        zip_unique = list(set(zip(downloaded_process_tracker_df.project_id, 
                                    downloaded_process_tracker_df.conversation_id)))
        for project_id, conversation_id in zip_unique:
            chunk_li = downloaded_process_tracker_df.loc[(downloaded_process_tracker_df.project_id == project_id) &
                        (downloaded_process_tracker_df.conversation_id == conversation_id)].chunk_id.unique()
            unprocessed_chunk_file_path_li = [os.path.join(self.download_root_dir, 
                                            conversation_id + '_' + chunk_id + '.wav') 
                                for chunk_id in chunk_li]
            counter = max(-1,self.process_tracker_df[self.process_tracker_df.conversation_id == 
                                          conversation_id].segment.max()) + 1
            while len(unprocessed_chunk_file_path_li) != 0:
                state_chunk_file_path_li = unprocessed_chunk_file_path_li
                output_filepath = os.path.join(self.segment_root_dir,
                                               conversation_id + '_' + str(counter) + '.wav')
                unprocessed_chunk_file_path_li = process_wav_files(unprocessed_chunk_file_path_li, 
                                                                   output_filepath,
                                                       max_size_mb = self.max_size_mb,
                                                       counter=counter)
                processed_chunk_file_path_li = [x for x in state_chunk_file_path_li if x not in unprocessed_chunk_file_path_li]
                if len(processed_chunk_file_path_li) == 0:
                    error_file = unprocessed_chunk_file_path_li[0]
                    segment_dict = {error_file.split('_')[-1].split('.')[0]: -1}
                    unprocessed_chunk_file_path_li = unprocessed_chunk_file_path_li[1:]
                else:
                    segment_dict = {file_path.split('_')[-1].split('.')[0]: counter 
                                    for file_path in processed_chunk_file_path_li}  # chunk to counter
                    self.process_tracker.update_segment(segment_dict)
                    counter = counter + 1
            # Remove downloaded files after processing
            for chunk_id in chunk_li:
                os.remove(os.path.join(self.download_root_dir,
                         conversation_id + '_' + chunk_id + '.wav'))
        
    def load(self) -> None:
        pass

    def run(self) -> None:
        self.extract()
        self.transform()
        self.load()

# if __name__ == "__main__":
#     import pandas as pd
#     from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker
#     process_tracker = ProcessTracker(pd.read_csv(
#         'server/dembrane/audio_lightrag/data/directus_etl_data/sample_conversation.csv'))
#     pipeline = AudioETLPipeline(process_tracker)
#     pipeline.run() 