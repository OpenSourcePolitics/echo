# import os

import numpy as np

# from lightrag.kg.postgres_impl import PostgreSQLDB
from dembrane.config import (
    AZURE_EMBEDDING_API_KEY,
    AZURE_EMBEDDING_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_EMBEDDING_DEPLOYMENT,
)
from dembrane.audio_lightrag.utils.azure_utils import setup_azure_client


async def embedding_func(texts: list[str]) -> np.ndarray:
    client = setup_azure_client(endpoint_uri = str(AZURE_EMBEDDING_ENDPOINT),
                                      api_key = str(AZURE_EMBEDDING_API_KEY),
                                      api_version = str(AZURE_OPENAI_API_VERSION))
    
    embedding = client.embeddings.create(model= str(AZURE_EMBEDDING_DEPLOYMENT), 
                                         input=texts)

    embeddings = [item.embedding for item in embedding.data]
    return np.array(embeddings)



# async def initialize_postgres_db():
#     """Initialize PostgreSQL database and ensure required tables exist."""
#     # Configure the database connection using environment variables
#     db_config = {
#         "host": os.getenv("PG_HOST"),
#         "port": os.getenv("PG_PORT"),
#         "user": os.getenv("PG_USER"),
#         "password": os.getenv("PG_PASSWORD"),
#         "database": os.getenv("PG_DB"),
#     }
    
#     # Create a PostgreSQLDB instance with the provided configuration
#     postgres_db = PostgreSQLDB(config=db_config)
    
#     # Initialize the database connection
#     await postgres_db.initdb()
    
#     # Check if the necessary tables exist; create them if they don't
#     await postgres_db.check_tables()
    
#     return postgres_db