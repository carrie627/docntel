import asyncio
import ollama

MODEL_NAME = "qwen2.5:3b"


def build_context(search_results):
    context = []

    for result in search_results:
        text = result.get("text")
        text_array = text.strip()
        cleaned_text = text_array[:300]

        if text:
            context.append(cleaned_text)

    return "\n\n".join(context)


def build_rag_prompt(context: str, question: str):
    return f"""
        You are a RAG assistant.

        Instructions:
        - Answer ONLY using the provided context.
        - Do not make up information.
        - If the answer is missing, say:
        "I could not find this information in the documents."

        Context:
        ----------------
        {context}
        ----------------

        Question:
        {question}

        Answer:
        """


async def stream_ai_response(prompt: str):
    stream = await asyncio.to_thread(
        ollama.chat,
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=True,
        options={
            "num_predict": 200,
            "temperature": 0.3
        }
    )

    for chunk in stream:
        content = chunk["message"]["content"]

        if content:
            yield content
