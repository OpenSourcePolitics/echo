import os

import pandas as pd
import pytest

from dembrane.audio_lightrag.main.run_etl import run_etl_pipeline


@pytest.mark.usefixtures("conversation_df", "project_df")
def test_run_etl_pipeline(conversation_df: pd.DataFrame, project_df: pd.DataFrame) -> None:
    # remove the json 
    json_path = "server/dembrane/audio_lightrag/data/JSON_Output/1f08cda8-2288-4fe3-b602-ea84e0d31688.json"
    if os.path.exists(json_path):
        os.remove(json_path)
    run_etl_pipeline([
        '1f08cda8-2288-4fe3-b602-ea84e0d31688',
    ])
    assert os.path.exists(json_path)
