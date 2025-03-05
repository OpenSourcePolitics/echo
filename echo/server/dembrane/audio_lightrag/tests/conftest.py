import os

import pandas as pd
import pytest

from dembrane.config import BASE_DIR


@pytest.fixture
def conversation_df() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(BASE_DIR, "dembrane/audio_lightrag/tests/data/test_conversation_df.csv"))
    return df

@pytest.fixture
def project_df() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(BASE_DIR, "dembrane/audio_lightrag/tests/data/test_project_df.csv"))
    return df.set_index('id')

@pytest.fixture
def test_audio_uuid() -> str:
    """Fixture providing a test UUID for audio files."""
    return 'e76ec7e1-8374-48a1-896b-7ea2d9863af9'
