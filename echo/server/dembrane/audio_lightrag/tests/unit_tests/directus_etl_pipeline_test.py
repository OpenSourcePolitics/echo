import os
import unittest
from dembrane.audio_lightrag.pipelines.directus_etl_pipeline import DirectusETLPipeline

class TestDirectusETLPipeline(unittest.TestCase):
    def setUp(self):
        self.directus_etl_pipeline = DirectusETLPipeline()

    def test_run(self):
        self.directus_etl_pipeline.run()
        self.assertTrue(os.path.exists("dembrane/audio_lightrag/data/directus_etl_data/conversation.csv"))
        self.assertTrue(os.path.exists("dembrane/audio_lightrag/data/directus_etl_data/project.csv"))
        os.remove("dembrane/audio_lightrag/data/directus_etl_data/conversation.csv")
        os.remove("dembrane/audio_lightrag/data/directus_etl_data/project.csv")
    

if __name__ == '__main__':
    unittest.main()
