import logging
from typing import Any, Dict, List, Tuple, Optional

# import yaml
import pandas as pd
from dotenv import load_dotenv
from directus_sdk_py import DirectusClient

from dembrane.config import (
    DIRECTUS_TOKEN,
    DIRECTUS_BASE_URL,
    AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH,
    AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH,
)

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
                                           "limit": 100000}}
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
        

    # def load_config(self, config_path: str) -> Dict[str, Any]:
    #     """Load the configuration file."""
    #     with open(config_path, "r") as file:
    #         return yaml.safe_load(file)

    def extract(self, conversation_id_list: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract data from the 'conversation' and 'project' collections
        from Directus.
        """
        # Request for conversations with their chunks
        if conversation_id_list is not None:
            self.conversation_request['query']['filter'] = {'id': {'_in': conversation_id_list}}
        conversation = self.directus_client.get_items("conversation", self.conversation_request)
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

    def load_df_to_directory(self, 
                             conversation_df: pd.DataFrame, 
                             project_df: pd.DataFrame,
                             conversation_output_path: str,
                             project_output_path: str) -> None:
        """
        Load the transformed data to CSV files.
        """
        conversation_df.rename(columns = {"id": "conversation_id"}).to_csv(conversation_output_path, index=False)
        project_df.to_csv(project_output_path, index=True)

        print(f"Conversation data saved to {conversation_output_path}")
        print(f"Project data saved to {project_output_path}")

    def run(self, 
            conversation_id_list: Optional[List[str]] = None,
            conversation_output_path: str | None = None,
            project_output_path: str | None = None) -> None:
        """Run the full ETL pipeline: extract, transform, and load."""
        if conversation_output_path is None:
            conversation_output_path = AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH
        if project_output_path is None:
            project_output_path = AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH
        conversation, project = self.extract(conversation_id_list=conversation_id_list)
        conversation_df, project_df = self.transform(conversation, project)
        self.load_df_to_directory(conversation_df, 
                                  project_df, 
                                  conversation_output_path, 
                                  project_output_path)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    pipeline = DirectusETLPipeline()
    pipeline.run([
            '02a12e46-7c33-4b78-9ab1-a5581f75c279',  # wav
            '9319fe3a-1c24-42d9-8750-4080f9197864',  # mp3
            '55b93782-cf12-4cc3-b6e8-2815997f7bde',  # m4a
            '35e13074-5f42-41de-b6c4-c2e651850730'   # mp4
        ])
