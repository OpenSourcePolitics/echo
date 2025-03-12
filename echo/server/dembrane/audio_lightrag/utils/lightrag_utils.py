# import os

import hashlib
import logging

import numpy as np
from lightrag.kg.postgres_impl import PostgreSQLDB

# from lightrag.kg.postgres_impl import PostgreSQLDB
from dembrane.config import (
    AZURE_EMBEDDING_API_KEY,
    AZURE_EMBEDDING_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_EMBEDDING_DEPLOYMENT,
)
from dembrane.audio_lightrag.utils.azure_utils import setup_azure_client

logger = logging.getLogger('audio_lightrag_utils')

async def embedding_func(texts: list[str]) -> np.ndarray:
    client = setup_azure_client(endpoint_uri = str(AZURE_EMBEDDING_ENDPOINT),
                                      api_key = str(AZURE_EMBEDDING_API_KEY),
                                      api_version = str(AZURE_OPENAI_API_VERSION))
    
    embedding = client.embeddings.create(model= str(AZURE_EMBEDDING_DEPLOYMENT), 
                                         input=texts)

    embeddings = [item.embedding for item in embedding.data]
    return np.array(embeddings)


async def check_audio_lightrag_tables(db: PostgreSQLDB) -> None:
    for _, table_definition in TABLES.items():
        await db.execute(table_definition)


async def upsert_transcript(db: PostgreSQLDB, 
                            document_id: str, 
                            content: str,
                            id: str | None = None,) -> None:
    if id is None:
        # generate random id
        s = str(document_id) + str(content)
        id = str(document_id) + '_' + str(int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16) % 10**8)
    
    content_embedding = await embedding_func([content])
    content_embedding = '[' + ','.join([str(x) for x in content_embedding[0]]) + ']'

    sql = SQL_TEMPLATES["UPSERT_TRANSCRIPT"].format(id=id, 
                                                    document_id=document_id, 
                                                    content=content, 
                                                    content_vector=content_embedding)
    await db.execute(sql)

async def fetch_query_transcript(db: PostgreSQLDB, 
                           query: str,
                           ids: list[str] | str | None = None,
                           limit: int = 10) -> list[str] | None:
    if ids is None:
        ids = 'NULL'
    else:
        ids = ','.join(["'" + str(id) + "'" for id in ids])
    
    
    query_embedding = await embedding_func([query])
    query_embedding = ','.join([str(x) for x in query_embedding[0]])
    sql = SQL_TEMPLATES["QUERY_TRANSCRIPT"].format(
        embedding_string=query_embedding, limit=limit, doc_ids=ids)
    result = await db.query(sql, multirows=True)
    return result

TABLES = {
    "LIGHTRAG_VDB_TRANSCRIPT": """
    CREATE TABLE IF NOT EXISTS LIGHTRAG_VDB_TRANSCRIPT (
    id VARCHAR(255),
    document_id VARCHAR(255),
    content VARCHAR(255),
    content_vector VECTOR,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    CONSTRAINT LIGHTRAG_VDB_TRANSCRIPT_PK PRIMARY KEY (id)
    )
    """
}

SQL_TEMPLATES = {
    "UPSERT_TRANSCRIPT": 
    """
        INSERT INTO LIGHTRAG_VDB_TRANSCRIPT (id, document_id, content, content_vector)
        VALUES ('{id}', '{document_id}', '{content}', '{content_vector}')
        ON CONFLICT (id) DO UPDATE SET
        document_id = '{document_id}',
        content = '{content}',
        content_vector = '{content_vector}'
    """, 
    "QUERY_TRANSCRIPT": 
    """
        WITH relevant_chunks AS (
            SELECT id as chunk_id
            FROM LIGHTRAG_VDB_TRANSCRIPT
            WHERE {doc_ids} IS NULL OR document_id = ANY(ARRAY[{doc_ids}])
        )
        SELECT content FROM
            (
                SELECT id, content,
                1 - (content_vector <=> '[{embedding_string}]'::vector) as distance
                FROM LIGHTRAG_VDB_TRANSCRIPT
                WHERE id IN (SELECT chunk_id FROM relevant_chunks)
            )
            ORDER BY distance DESC
            LIMIT {limit}
    """
}



