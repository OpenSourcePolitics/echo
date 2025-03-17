import os
import unittest

from dembrane.config import (
    BASE_DIR,
)
from dembrane.audio_lightrag.pipelines.directus_etl_pipeline import DirectusETLPipeline
from dembrane.config import (
    AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH,
    AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH,
)

class TestDirectusETLPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.directus_etl_pipeline = DirectusETLPipeline()

    def test_run(self) -> None:
        # AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH = os.path.join(BASE_DIR, "dembrane/audio_lightrag/tests/data/test_conversation_df.csv")
        # AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH= os.path.join(BASE_DIR, "dembrane/audio_lightrag/tests/data/test_project_df.csv")
        self.directus_etl_pipeline.run(conversation_output_path=AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH,
                                       project_output_path=AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH)
        self.assertTrue(os.path.exists(AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH))
        self.assertTrue(os.path.exists(AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH))
    

if __name__ == '__main__':
    unittest.main()
