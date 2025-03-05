import pandas as pd
from dotenv import load_dotenv

from dembrane.config import (
    AZURE_OPENAI_AUDIOMODEL_API_KEY,
    AZURE_OPENAI_AUDIOMODEL_ENDPOINT,
    AZURE_OPENAI_AUDIOMODEL_API_VERSION,
    AZURE_OPENAI_TEXTSTRUCTUREMODEL_NAME,
    AZURE_OPENAI_TEXTSTRUCTUREMODEL_API_KEY,
    AZURE_OPENAI_TEXTSTRUCTUREMODEL_ENDPOINT,
    AZURE_OPENAI_TEXTSTRUCTUREMODEL_API_VERSION,
)
from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker
from dembrane.audio_lightrag.pipelines.audio_etl_pipeline import AudioETLPipeline
from dembrane.audio_lightrag.pipelines.directus_etl_pipeline import DirectusETLPipeline

# from dembrane.audio_lightrag.pipelines.lightrag_etl_pipeline import LightragETLPipeline
from dembrane.audio_lightrag.pipelines.contextual_chunk_etl_pipeline import (
    ContextualChunkETLPipeline,
)

load_dotenv()

def run_etl_pipeline(conv_id_list: list[str]) -> None:
    """
    Runs the complete ETL pipeline including Directus, Audio, Contextual Chunk, and Lightrag processes.
    """
    
    # Run Directus ETL
    directus_pl = DirectusETLPipeline()
    directus_pl.run(conv_id_list)

    # Initialize process tracker
    process_tracker = ProcessTracker(
        conversation_df=pd.read_csv('server/dembrane/audio_lightrag/data/directus_etl_data/conversation.csv'),
        project_df=pd.read_csv('server/dembrane/audio_lightrag/data/directus_etl_data/project.csv').set_index('id')
    )

    # Run Audio ETL
    audio_pl = AudioETLPipeline(process_tracker)
    audio_pl.run()

    # Run Contextual Chunk ETL
    contextual_chunk_pl = ContextualChunkETLPipeline(process_tracker,
                                                     audio_model_endpoint_uri = str(AZURE_OPENAI_AUDIOMODEL_ENDPOINT),
                                                     audio_model_api_key = str(AZURE_OPENAI_AUDIOMODEL_API_KEY),
                                                     audio_model_api_version = str(AZURE_OPENAI_AUDIOMODEL_API_VERSION),
                                                     text_structuring_model_endpoint_uri = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_ENDPOINT),
                                                     text_structuring_model_api_key = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_API_KEY),
                                                     text_structuring_model_api_version = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_API_VERSION),
                                                     text_structuring_model_name = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_NAME)
                                                     )
    contextual_chunk_pl.run()
    process_tracker.delete_temps()

if __name__ == "__main__":
    run_etl_pipeline([
        '02a12e46-7c33-4b78-9ab1-a5581f75c279',  # wav
    ])
