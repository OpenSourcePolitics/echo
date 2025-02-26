import json

import pandas as pd
import pytest

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
from dembrane.audio_lightrag.pipelines.contextual_chunk_etl_pipeline import (
    ContextualChunkETLPipeline,
)


@pytest.mark.usefixtures("conversation_df", "project_df")
def test_Contextual_chunk_etl_pipeline(conversation_df: pd.DataFrame, project_df: pd.DataFrame) -> None:
    test_conversation_id = conversation_df.conversation_id.unique()[0]
    process_tracker = ProcessTracker(conversation_df = conversation_df[
        conversation_df.conversation_id==test_conversation_id],
        project_df = project_df)
    audio_etl_pipeline = AudioETLPipeline(process_tracker)
    audio_etl_pipeline.run()
    contextual_chunk_pipeline = ContextualChunkETLPipeline(process_tracker,
                                                           audio_model_endpoint_uri = str(AZURE_OPENAI_AUDIOMODEL_ENDPOINT),
                                                            audio_model_api_key = str(AZURE_OPENAI_AUDIOMODEL_API_KEY),
                                                            audio_model_api_version = str(AZURE_OPENAI_AUDIOMODEL_API_VERSION),
                                                            text_structuring_model_endpoint_uri = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_ENDPOINT),
                                                            text_structuring_model_api_key = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_API_KEY),
                                                            text_structuring_model_api_version = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_API_VERSION),
                                                            text_structuring_model_name = str(AZURE_OPENAI_TEXTSTRUCTUREMODEL_NAME))
    contextual_chunk_pipeline.run()
   
    with open('server/dembrane/audio_lightrag/data/JSON_Output/' + test_conversation_id + '.json') as f:
        responses = json.load(f)
    assert (len(responses) == len(process_tracker().segment.unique()))
    assert set(responses[test_conversation_id + '_0.0'].keys()) == set(['TRANSCRIPT','CONTEXTUAL_TRANSCRIPT'])
    process_tracker.delete_temps()
