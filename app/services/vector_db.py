import os
import asyncio
import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient, models
from ..core.config import get_settings
from llama_index.core import SimpleDirectoryReader

settings = get_settings()

encoder_model = None
client = None

COLLECTION_NAME = "docntel_vector_db"


async def ensure_payload_index(field_name, schema_type):

    collection_info = await client.get_collection(
        COLLECTION_NAME
    )

    existing_schema = collection_info.payload_schema

    if field_name not in existing_schema:

        await client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=schema_type
        )


async def init_vector_db():
    global encoder_model
    global client

    if encoder_model is None:
        encoder_model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1.5",
            trust_remote_code=True
        )

    if client is None:
        client = AsyncQdrantClient(
            url=settings.qdrant_cloud_url,
            api_key=settings.qdrant_cloud_api_key
        )

    if not await client.collection_exists(COLLECTION_NAME):
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=768,
                distance=models.Distance.COSINE,
            ),
            hnsw_config=models.HnswConfigDiff(
                m=16,
                ef_construct=200,
                full_scan_threshold=1000,
            ),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=100
            )
        )

    await ensure_payload_index("user_id", models.PayloadSchemaType.UUID)
    await ensure_payload_index("doc_id", models.PayloadSchemaType.UUID)
    await ensure_payload_index("source", models.PayloadSchemaType.KEYWORD)


def words_sliding_window_chunker(text, window=200, stride=100):
    words = text.split()
    chunks = []

    for i in range(0, len(words) - window + 1, stride):
        chunk = " ".join(words[i:i + window])
        chunks.append(chunk)
    return chunks


async def generate_embeddings(texts, is_query: bool = False):

    prefix = "search_query: " if is_query else "search_document: "
    formatted = [
        f"{prefix}{text}"
        for text in texts
    ]

    embeddings = await asyncio.to_thread(encoder_model.encode, formatted)
    return embeddings.tolist()


def extract_text_from_doc(path):
    reader = SimpleDirectoryReader(
        input_files=[path],
        required_exts=[".pdf", ".docx", ".txt"]
    )
    docs = reader.load_data()

    if not docs:
        return ""

    texts = []

    for doc in docs:
        texts.append(doc.text)

    return "\n".join(texts)


async def extract_document_and_save(path, current_user_id, doc_id, filename):
    texts = await asyncio.to_thread(extract_text_from_doc, path)
    chunks = words_sliding_window_chunker(texts)

    embeddings = await generate_embeddings(chunks)

    points = []
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{doc_id}_{idx}"
            )
        )
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "user_id": current_user_id,
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "text": chunk,
                    "source": filename
                }
            )
        )

    await client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )


async def search_documents(
    query: str,
    current_user_id: str,
    limit: int = 5
):

    if not query.strip():
        return []

    query_embedding = await generate_embeddings(
        [query],
        is_query=True
    )

    results = await client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding[0],
        limit=limit,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(
                        value=current_user_id
                    )
                )
            ]
        )
    )

    return [
        {
            "text": point.payload["text"],
            "score": point.score,
            "source": point.payload["source"],
            "doc_id": point.payload["doc_id"]
        }
        for point in results.points
    ]
