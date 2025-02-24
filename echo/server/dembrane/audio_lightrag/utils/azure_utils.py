from openai import AzureOpenAI
import os
def setup_azure_client(endpoint_uri, api_key,
                       api_version):
    """
    Setup Azure OpenAI client with the provided credentials
    
    Parameters:
    endpoint_uri (str): The Azure endpoint URI
    api_key (str): Your Azure API key
    
    Returns:
    AzureOpenAI: Configured client
    """
    client = AzureOpenAI(
        azure_endpoint=endpoint_uri,
        api_key=api_key,
        api_version=api_version 
    )
    return client