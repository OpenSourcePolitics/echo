import os
import unittest

from dembrane.config import (
    AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH,
    AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH,
)
from dembrane.audio_lightrag.pipelines.directus_etl_pipeline import DirectusETLPipeline


class TestDirectusETLPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.directus_etl_pipeline = DirectusETLPipeline()

    def test_run(self) -> None:
        print("**********Running test_run**********")
        self.directus_etl_pipeline.run()
        self.assertTrue(os.path.exists(AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH))
        self.assertTrue(os.path.exists(AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH))
        os.remove(AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH)
        os.remove(AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH)
    

if __name__ == '__main__':
    unittest.main()
