import os
import shutil

import pandas as pd


class ProcessTracker:
    def __init__(self, 
                 conversation_df: pd.DataFrame, 
                 project_df: pd.DataFrame,
                 conversation_df_path: str = 'server/dembrane/audio_lightrag/data/progress_tracker.csv', 
                 ) -> None:
        """
        Initialize the ProcessTracker.

        Args:
        - df (pd.DataFrame): DataFrame containing the information to be tracked.
        - df_path (str): Path to save the DataFrame.
        """
        self.df = conversation_df
        self.df_path = conversation_df_path
        self.project_df = project_df
        # Ensure the columns are present
        if 'download_status' not in conversation_df.columns:
            self.df['download_status'] = None
        if 'segment' not in conversation_df.columns:
            self.df['segment'] = None
        if 'log' not in conversation_df.columns:
            self.df['log'] = None
        if 'json_status' not in conversation_df.columns:
            self.df['json_status'] = None
        if 'ligtrag_status' not in conversation_df.columns:
            self.df['ligtrag_status'] = None
        self.project_df = project_df


    def __call__(self) -> pd.DataFrame:
        return self.df
    
    def update_download_status(self, conversation_id: int, chunk_id: int, status: str) -> None:
        """
        Update the download status of a given conversation and chunk id.

        Args:
        - conversation_id (int): The id of the conversation.
        - chunk_id (int): The id of the chunk.
        - status (str): The status of the download. Should be either 'pass' or 'fail'.
        """
        self.df.loc[(self.df.conversation_id == conversation_id) & 
                    (self.df.chunk_id == chunk_id), 'download_status'] = status
        self.save_df()

    def update_segment(self, dict: dict) -> None:
        """
        Update the segment column of the DataFrame with the given
        dictionary.

        Args:
        - dict (dict): A dictionary where the keys are chunk ids and the values
        are the segment numbers.
        """
        for chunk_id, segment in dict.items():
            # Update the segment column
            self.df.loc[(self.df.chunk_id == chunk_id), 'segment'] = segment
        # Save the DataFrame
        self.save_df()
        
    def update_json_status(self, conversation_id: int, segment: int, status: str) -> None:
        self.df.loc[(self.df.conversation_id == conversation_id) & (self.df.segment == segment), 'json_status'] = status
        self.save_df()

    def update_ligtrag_status(self, conversation_id: int, status: str) -> None:
        self.df.loc[(self.df.conversation_id == conversation_id) , 'ligtrag_status'] = status
        self.save_df()

    def save_df(self) -> None:
        """
        Save the DataFrame to the given path.
        """
        self.df.to_csv(self.df_path, index=False)
    
    def get_project_df(self) -> pd.DataFrame: 
        return self.project_df
    
    def delete_temps(self,
                     temp_dir_lis: list[str] = ['server/dembrane/audio_lightrag/data/Temp_Downloads','server/dembrane/audio_lightrag/data/Temp_Segments']
                     ) -> None:
        for temp_dir in temp_dir_lis:
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

