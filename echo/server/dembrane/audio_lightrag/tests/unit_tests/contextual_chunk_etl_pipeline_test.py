from dembrane.audio_lightrag.pipelines.contextual_chunk_etl_pipeline import ContaxtualChunkETLPipeline
from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker
import pandas as pd
import pytest
from dembrane.audio_lightrag.pipelines.audio_etl_pipeline import AudioETLPipeline   


@pytest.mark.usefixtures("conversation_df", "project_df")
def test_contaxtual_chunk_etl_pipeline(conversation_df: pd.DataFrame, project_df: pd.DataFrame):
    test_conversation_id = '02a12e46-7c33-4b78-9ab1-a5581f75c279'
    process_tracker = ProcessTracker(conversation_df = conversation_df[
        conversation_df.conversation_id==test_conversation_id],
        project_df = project_df)
    audio_etl_pipeline = AudioETLPipeline(process_tracker)
    audio_etl_pipeline.run()
    contextual_chunk_pipeline = ContaxtualChunkETLPipeline(process_tracker)
    contextual_chunk_pipeline.run()
    import json 
    with open('server/dembrane/audio_lightrag/data/JSON_Output/' + test_conversation_id + '.json') as f:
        responses = json.load(f)
    assert (len(responses) == len(process_tracker().segment.unique()))
    assert set(responses[test_conversation_id + '_0.0'].keys()) == set(['TRANSCRIPT','CONTEXTUAL_TRANSCRIPT'])
    process_tracker.delete_temps()
