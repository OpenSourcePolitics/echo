import unittest

import pytest

# from dembrane.config import (
#     BASE_DIR,
#     AUDIO_LIGHTRAG_PROJECT_OUTPUT_PATH,
#     AUDIO_LIGHTRAG_CONVERSATION_OUTPUT_PATH,
# )
from dembrane.audio_lightrag.pipelines.directus_etl_pipeline import DirectusETLPipeline


class TestDirectusETLPipeline:
    @pytest.fixture
    def directus_etl_pipeline(self) -> DirectusETLPipeline:
        return DirectusETLPipeline()

    def test_run(self, directus_etl_pipeline: DirectusETLPipeline) -> None:
        process_tracker = directus_etl_pipeline.run()
        assert process_tracker().shape[0] * process_tracker().shape[1] > 0

if __name__ == '__main__':
    unittest.main()
