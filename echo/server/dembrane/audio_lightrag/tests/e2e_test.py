from dembrane.audio_lightrag.main.run_etl import run_etl_pipeline
import os
import pytest
import pandas as pd

@pytest.mark.usefixtures("conversation_df", "project_df")
def test_run_etl_pipeline(conversation_df: pd.DataFrame, project_df: pd.DataFrame):
    # remove the json 
    json_path = "server/dembrane/audio_lightrag/data/JSON_Output/02a12e46-7c33-4b78-9ab1-a5581f75c279.json"
    if os.path.exists(json_path):
        os.remove(json_path)
    run_etl_pipeline([
        '02a12e46-7c33-4b78-9ab1-a5581f75c279',  # wav
    ])
    assert os.path.exists(json_path)
