from logging import getLogger

from fastapi import Request, APIRouter, HTTPException
from litellm import completion
from pydantic import BaseModel
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from lightrag.lightrag import QueryParam

logger = getLogger("api.stateless")

StatelessRouter = APIRouter(tags=["stateless"])


class TranscriptRequest(BaseModel):
    system_prompt: str | None = None
    transcript: str
    language: str | None = None


class TranscriptResponse(BaseModel):
    summary: str


class InsertRequest(BaseModel):
    content: str | list[str]
    id: str | list[str] | None = None

class InsertResponse(BaseModel):
    status: str
    result: dict


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    status: str
    result: str


@StatelessRouter.post("/summarize")
async def summarize_conversation_transcript(
    # auth: DependencyDirectusSession,
    body: TranscriptRequest,
) -> TranscriptResponse:
    # Use the provided transcript and system prompt (if any) for processing
    system_prompt = body.system_prompt
    transcript = body.transcript

    # Generate a summary from the transcript (placeholder logic)
    summary = generate_summary(transcript, system_prompt, body.language)

    # Return the full transcript as a single string
    return TranscriptResponse(summary=summary)


def generate_summary(transcript: str, system_prompt: str | None, language: str | None) -> str:
    """
    Generate a summary of the transcript using LangChain and a custom API endpoint.

    Args:
        transcript (str): The conversation transcript to summarize.
        system_prompt (str | None): Additional context or instructions for the summary.

    Returns:
        str: The generated summary.
    """
    # Prepare the prompt template
    base_prompt = f"You are a helpful assistant. Please provide a summary of the following transcript. Only return the summary itself, do not include any other text. Focus on the most important points of the text. The language of the summary must be in {language}."
    if system_prompt:
        base_prompt += f"\nContext (ignore if None): {system_prompt}"

    prompt_template = ChatPromptTemplate.from_messages(
        [HumanMessagePromptTemplate.from_template(f"{base_prompt}\n\n{{transcript}}")]
    )
    # Call the model over the provided API endpoint
    response = completion(
        # model="ollama/llama3.1:8b",
        # api_base="https://llm-demo.ai-hackathon.haven.vng.cloud",
        model="anthropic/claude-3-5-sonnet-20240620",
        messages=[
            {
                "content": prompt_template.format_prompt(transcript=transcript).to_messages(),
                "role": "user",
            }
        ],
    )

    response_content = response["choices"][0]["message"]["content"]

    return response_content


@StatelessRouter.post("/rag/insert")
async def insert_item(request: Request, payload: InsertRequest) -> InsertResponse:
    rag = request.app.state.rag
    if rag is None:
        raise HTTPException(status_code=500, detail="RAG object not initialized")
    try:
        # Insert the content and create a default result dictionary
        rag.insert(payload.content, payload.id)
        result = {"status": "inserted", "content": payload.content}
        return InsertResponse(status="success", result=result)
    except Exception as e:
        logger.exception("Insert operation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@StatelessRouter.post("/rag/query")
async def query_item(request: Request, payload: QueryRequest) -> QueryResponse:
    rag = request.app.state.rag
    if rag is None:
        raise HTTPException(status_code=500, detail="RAG object not initialized")
    try:
        result = rag.query(payload.query, param=QueryParam(mode="local"))
        return QueryResponse(status="success", result=result)
    except Exception as e:
        logger.exception("Query operation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
