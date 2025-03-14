# from dotenv import load_dotenv
import os
import glob
import json
from logging import getLogger

# import yaml
import pandas as pd
import requests

from dembrane.config import (
    API_BASE_URL,
    AUDIO_LIGHTRAG_SEGMENT_DIR,
    AUDIO_LIGHTRAG_OUTPUT_JSON_FILEPATH,
    AUDIO_LIGHTRAG_CONVERSATION_HISTORY_NUM,
)
from dembrane.audio_lightrag.utils.prompts import Prompts
from dembrane.audio_lightrag.utils.azure_utils import setup_azure_client
from dembrane.audio_lightrag.utils.open_ai_utils import get_json_dict_from_audio
from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker

logger = getLogger("audio_lightrag.pipelines.contextual_chunk_etl_pipeline")

class ContextualChunkETLPipeline:
    def __init__(self,
                 process_tracker:ProcessTracker,
                 audio_model_endpoint_uri:str,
                 audio_model_api_key:str,
                 audio_model_api_version:str,
                 text_structuring_model_endpoint_uri:str,
                 text_structuring_model_api_key:str,
                 text_structuring_model_api_version:str,
                 text_structuring_model_name:str = 'text_structuring_model',) -> None:
        self.audio_model_endpoint_uri = audio_model_endpoint_uri
        self.audio_model_api_key = audio_model_api_key
        self.audio_model_api_version = audio_model_api_version
        self.text_structuring_model_endpoint_uri = text_structuring_model_endpoint_uri
        self.text_structuring_model_api_key = text_structuring_model_api_key
        self.text_structuring_model_api_version = text_structuring_model_api_version
        self.text_structuring_model_name = text_structuring_model_name
        # Setup Azure clients
        self.audio_model_client = setup_azure_client(audio_model_endpoint_uri, 
                                                     audio_model_api_key, audio_model_api_version)
        self.text_structuring_model_client = setup_azure_client(text_structuring_model_endpoint_uri, 
                                                                text_structuring_model_api_key,
                                                                text_structuring_model_api_version)
    
        # self.config = self.load_config(config_path)
        self.output_json_filepath = AUDIO_LIGHTRAG_OUTPUT_JSON_FILEPATH
        self.audio_filepath_li = glob.glob(AUDIO_LIGHTRAG_SEGMENT_DIR+'/*')
        self.conversation_history_num = AUDIO_LIGHTRAG_CONVERSATION_HISTORY_NUM
        # Create a temporary dataframe to maintain order of file: Big files in have '*_1-1.*' type of names 
        self.temp_segments_df = pd.DataFrame({'audio_filepath':self.audio_filepath_li})
        self.temp_segments_df['segment_index'] = self.temp_segments_df.audio_filepath.apply(lambda audio_filepath: float(audio_filepath.split('_')[-1].split('.')[0].replace('-','.')))
        self.temp_segments_df['conversation_id'] = self.temp_segments_df.audio_filepath.apply(lambda audio_filepath: audio_filepath.split('/')[-1].split('_')[0])
        self.temp_segments_df['conversationid_segmentfloat'] = self.temp_segments_df.conversation_id + '_' + self.temp_segments_df.segment_index.apply(lambda x: f'{x:.4f}').astype('str')
        self.temp_segments_df.sort_values('segment_index', inplace = True)
        self.process_tracker = process_tracker
        self.process_tracker_df = process_tracker()
        self.valid_process_tracker_df = self.process_tracker_df[self.process_tracker_df.segment.dropna()>=0]
        self.api_base_url = API_BASE_URL
    def extract(self) -> None:pass 
    def transform(self) -> None:
        for conversation_id in self.valid_process_tracker_df[self.valid_process_tracker_df.json_status.isna()].conversation_id.unique():
            output_json_filepath = os.path.join(self.output_json_filepath, conversation_id+'.json')
            if os.path.isfile(output_json_filepath):
                    with open(output_json_filepath) as f:
                        responses = json.load(f)
            else:
                responses = {}
                with open(output_json_filepath,'w') as f:
                    json.dump(responses,f)


            project_id = self.valid_process_tracker_df[self.valid_process_tracker_df.conversation_id == conversation_id].project_id.unique()[0]
            event_text = '\n\n'.join([f"{k} : {v}" for k,v in self.process_tracker.get_project_df().loc[project_id].to_dict().items()])
            conversation_segments_df = self.temp_segments_df[self.temp_segments_df['conversation_id'] == conversation_id]
            for _,row in conversation_segments_df.iterrows():
                previous_respenses_text = '\n\n'.join([previous_conversation['CONTEXTUAL_TRANSCRIPT']
                                                for previous_conversation in 
                                                list(responses.values())[-int(self.conversation_history_num):]])
                audio_model_prompt = Prompts.audio_model_system_prompt()
                audio_model_prompt = audio_model_prompt.format(event_text = event_text, 
                                        previous_conversation_text = previous_respenses_text)
                if row.conversationid_segmentfloat not in responses.keys():
                    try:
                        responses[row.conversationid_segmentfloat] = get_json_dict_from_audio(wav_loc = row.audio_filepath,
                                                                               audio_model_prompt=audio_model_prompt,
                                                                               audio_model_client=self.audio_model_client,
                                                                               text_structuring_model_client=self.text_structuring_model_client,
                                                                               text_structuring_model_name=self.text_structuring_model_name)
                        
                        self.process_tracker.update_json_status(conversation_id, 
                                                        row.segment_index,
                                                        'pass')
                        
                        # Insert the transcript into LightRAG
                        response = requests.post(
                            f"{self.api_base_url}/api/stateless/rag/insert",
                            json={"content": responses[row.conversationid_segmentfloat]['CONTEXTUAL_TRANSCRIPT'],
                                  "id": row.conversationid_segmentfloat,
                                  "transcripts": responses[row.conversationid_segmentfloat]['TRANSCRIPTS']}
                        )

                        if response.status_code == 200:
                            self.process_tracker.update_ligtrag_status(conversation_id, 
                                            row.segment_index,
                                            'pass')
                        else:
                            logger.info("Error in inserting transcript into LightRAG. Check API health")
                            self.process_tracker.update_ligtrag_status(conversation_id, 
                                            row.segment_index,
                                            'fail')
                        
                    except Exception as e:
                        logger.exception(f"Error in inserting transcript into LightRAG : {e}")
                        self.process_tracker.update_json_status(conversation_id, 
                                            row.segment_index,
                                            'fail')
                with open(output_json_filepath,'w') as f:
                    json.dump(responses,f)

    def load(self) -> None:pass

    def run(self) -> None:
        self.extract()
        self.transform()
        self.load()
            

# if __name__ == "__main__":
    # from dembrane.audio_lightrag.utils.process_tracker import ProcessTracker
    # import pandas as pd
    # # load_dotenv()
    # # audio_model_endpoint_uri = os.getenv("AZURE_OPENAI_AUDIOMODEL_ENDPOINT")
    # # audio_model_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    # # audio_model_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    # # text_structuring_model_endpoint_uri = os.getenv("AZURE_OPENAI_TEXTSTRUCTUREMODEL_ENDPOINT")
    # # text_structuring_model_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    # # text_structuring_model_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    # # pipeline = ContextualChunkETLPipeline(audio_model_endpoint_uri, audio_model_api_key, audio_model_api_version,
    # #              text_structuring_model_endpoint_uri, text_structuring_model_api_key, text_structuring_model_api_version)
    # process_tracker = ProcessTracker(pd.read_csv('server/dembrane/audio_lightrag/data/progress_tracker.csv'), 
    #                                  project_df = pd.read_csv('server/dembrane/audio_lightrag/data/directus_etl_data/project.csv').set_index('id'))
    # pipeline = ContextualChunkETLPipeline('/home/azureuser/cloudfiles/code/Users/arindamroy11235/experiments/server/dembrane/audio_lightrag/configs/contextual_chunk_etl_pipeline_config.yaml',
    #                                       process_tracker)
    # pipeline.run()
