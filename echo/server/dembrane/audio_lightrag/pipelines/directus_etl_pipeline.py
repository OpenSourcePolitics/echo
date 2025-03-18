import logging
from typing import Any, Dict, List, Tuple, Optional

# import yaml
import pandas as pd
from dotenv import load_dotenv
from directus_sdk_py import DirectusClient

from dembrane.config import (
    DIRECTUS_TOKEN,
    DIRECTUS_BASE_URL,
)
from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker

logger = logging.getLogger("dembrane.audio_lightrag.pipelines.directus_etl_pipeline")

class DirectusETLPipeline:
    """
    A class for extracting, transforming, and loading data from Directus.
    """
    def __init__(self) -> None:
        # Load environment variables from the .env file
        load_dotenv()

        # Get accepted formats from config
        self.accepted_formats = ['wav', 'mp3', 'm4a', 'ogg']

        self.project_request = {"query": {"fields": 
                                                ["id", "name", "language", "context", 
                                                "default_conversation_title", 
                                                "default_conversation_description"], 
                                           "limit": 100000,
                                           "filter": {"id": {"_in": []}}}}
        self.conversation_request = {"query": 
                                     {"fields": ["id", "project_id", 
                                                 "chunks.id", "chunks.path", 
                                                 "chunks.timestamp"], 
                                           "limit": 100000,
                                           "deep": {"chunks": 
                                                    {"_limit": 100000, "_sort": "timestamp"}
                                                    }
                                                }
                                    }

        # Initialize the Directus client using sensitive info from environment variables
        self.directus_client = DirectusClient(DIRECTUS_BASE_URL, DIRECTUS_TOKEN)

    def extract(self, conversation_id_list: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract data from the 'conversation' and 'project' collections
        from Directus.
        """
        # Request for conversations with their chunks
        if conversation_id_list is not None:
            self.conversation_request['query']['filter'] = {'id': {'_in': conversation_id_list}}
        conversation = self.directus_client.get_items("conversation", self.conversation_request)
        project_id_list = list(set([conversation_request['project_id'] for conversation_request in conversation]))
        self.project_request['query']['filter'] = {'id': {'_in': project_id_list}}
        project = self.directus_client.get_items("project", self.project_request)
        return conversation, project

    def transform(self, conversation: List[Dict[str, Any]], project: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Transform the extracted data into structured pandas DataFrames.
        """
        # Process conversation data
        conversation_df = pd.DataFrame(conversation)

        # Filter out conversations with no chunks
        conversation_df = conversation_df[conversation_df.chunks.apply(lambda x: len(x) != 0)]

        # Convert each chunk's dictionary values to a list
        conversation_df['chunks_id_path_ts'] = conversation_df.chunks.apply(
            lambda chunks: [list(chunk.values()) for chunk in chunks]
        )

        # Explode the list of chunks so that each row represents one chunk
        conversation_df = conversation_df.explode('chunks_id_path_ts')

        # Create separate columns for chunk_id, path, and timestamp
        conversation_df[['chunk_id', 'path', 'timestamp']] = pd.DataFrame(
            conversation_df['chunks_id_path_ts'].tolist(), index=conversation_df.index
        )

        # Reset index and select only necessary columns; drop any rows with missing values
        conversation_df = conversation_df.reset_index(drop=True)
        conversation_df = conversation_df[['id', 'project_id', 'chunk_id', 'path', 'timestamp']].dropna()

        # Determine the format from the file path
        conversation_df['format'] = conversation_df.path.apply(lambda x: x.split('.')[-1])

        # Filter rows based on accepted formats from config
        conversation_df = conversation_df[conversation_df.format.isin(self.accepted_formats)]

        # Set the conversation id as the index and sort the DataFrame
        conversation_df.rename(columns = {"id": "conversation_id"}, inplace=True)
        # conversation_df.set_index('conversation_id', inplace=True)
        conversation_df = conversation_df.sort_values(['project_id', 'conversation_id', 'timestamp'])

        # Process project data
        project_df = pd.DataFrame(project)
        project_df.set_index('id', inplace=True)

        if conversation_df.empty:
            logger.warning("No conversation data found")
        if project_df.empty:
            logger.warning("No project data found")

        return conversation_df, project_df

    def load_to_process_tracker(self, 
                                conversation_df: pd.DataFrame, 
                                project_df: pd.DataFrame) -> ProcessTracker:
        """
        Load the transformed data to a process tracker.
        """
        return ProcessTracker(conversation_df, project_df)

    def run(self, conversation_id_list: Optional[List[str]] = None) -> ProcessTracker:
        """Run the full ETL pipeline: extract, transform, and load."""
        conversation, project = self.extract(conversation_id_list=conversation_id_list)
        conversation_df, project_df = self.transform(conversation, project)
        process_tracker = self.load_to_process_tracker(conversation_df, project_df)
        return process_tracker
