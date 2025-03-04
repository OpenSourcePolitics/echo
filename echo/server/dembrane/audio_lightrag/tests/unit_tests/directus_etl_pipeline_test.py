import os
import unittest

from dembrane.audio_lightrag.pipelines.directus_etl_pipeline import DirectusETLPipeline


class TestDirectusETLPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.directus_etl_pipeline = DirectusETLPipeline()

    def test_run(self) -> None:
        print("**********Running test_run**********")
        self.directus_etl_pipeline.run()
        self.assertTrue(os.path.exists("server/dembrane/audio_lightrag/data/directus_etl_data/conversation.csv"))
        self.assertTrue(os.path.exists("server/dembrane/audio_lightrag/data/directus_etl_data/project.csv"))
        os.remove("server/dembrane/audio_lightrag/data/directus_etl_data/conversation.csv")
        os.remove("server/dembrane/audio_lightrag/data/directus_etl_data/project.csv")
    

if __name__ == '__main__':
    unittest.main()
