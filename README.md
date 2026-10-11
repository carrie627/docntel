# Docntel AI — Backend

A document intelligence API that enables users to upload documents and ask questions about their content using retrieval-augmented generation (RAG).

## Tech Stack

- **API:** Python, FastAPI
- **Database:** PostgreSQL, SQLModel
- **Vector Database:** Qdrant
- **AI:** Local LLMs and embedding models via Ollama
- **Authentication:** JWT-based authentication

## Key Features

- Document upload and processing for AI-powered retrieval.
- Semantic search and context-aware question answering.
- User authentication and access isolation.
- Chat and message management.
- WebSocket-based chat response streaming.

## Architecture

FastAPI handles API requests and business logic, PostgreSQL stores application data, and Qdrant indexes document embeddings for semantic retrieval. Retrieved context is used to generate answers through a locally hosted language model.

## Running Locally

Configure the required environment variables and services for PostgreSQL, Qdrant, and Ollama, then install the Python dependencies and start the FastAPI application.

See the application configuration and dependency files for setup details.

## Engineering Focus

This project explores secure API design, relational data modeling, retrieval-augmented generation, and real-time communication without relying on paid LLM APIs.

## Current Status

The project was deployed using free-tier infrastructure for demonstration purposes. The hosted demo is currently unavailable due to hosting limitations. Local execution requires the supporting services described above.

