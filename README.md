# Company Knowledge Assistant — Agentic RAG Chatbot

An internal, production-ready **Agentic Retrieval-Augmented Generation (RAG) Chatbot** that allows users to upload collections of PDF documents and ask questions grounded strictly in their content.

Built with Python, FastAPI, ChromaDB, SentenceTransformers, and a clean, lightweight HTML/CSS/JS frontend.

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph UI ["User Interface (Frontend)"]
        User[User] -->|Upload PDFs| Dropzone[PDF Uploader]
        User -->|Ask Question| ChatBox[Chat Input]
    end

    subgraph Backend ["FastAPI Backend Layer"]
        Dropzone -->|POST /api/upload| Ingest[Ingestion Module (pypdf)]
        Ingest -->|Extracted Pages & Meta| Chunker[Chunking Module]
        Chunker -->|Chunks with Meta| Embedder[Local SentenceTransformer Embeddings]
        Embedder -->|Dense Vectors| VectorDB[(ChromaDB Vector Store)]
        
        ChatBox -->|POST /api/chat| Agent[Agentic RAG Engine]
        
        subgraph AgenticLoop ["Agentic Decision Loop"]
            Agent -->|1. Evaluate Intent| Router{Needs Document Search?}
            Router -->|No (e.g. Math / Greetings)| DirectAnswer[Direct Answer Generator]
            Router -->|Yes (e.g. Policy Query)| QueryFormulator[Search Query Formulator]
            
            QueryFormulator -->|2. Call Tool| RAGTool[PDF Retrieval Tool]
            RAGTool -->|3. Cosine Similarity Search| VectorDB
            VectorDB -->|4. Top Matching Passages + Metadata| RAGTool
            RAGTool -->|5. Formatted Context & Citations| Agent
            
            Agent -->|6. Grounded Prompting| LLMProvider[LLM (Gemini / OpenAI)]
        end
        
        LLMProvider -->|Grounded Response| Formatter[Response & Citation Formatter]
        DirectAnswer --> Formatter
    end

    Formatter -->|Answer + Source Badges| UI
```

---

## 1. What the Project Does

The **Company Knowledge Assistant** is designed for internal enterprise use. It enables employees to ingest policy handbooks, technical documentation, standard operating procedures, and compliance guidelines, and then query the knowledge base in natural language.

### Key Capabilities:
- **PDF Ingestion & Metadata Tracking**: Extracts text page-by-page and maintains exact filename, page number, and chunk references.
- **Agentic Intent Routing**: Smart router determines whether a question requires searching internal documents or can be answered directly (e.g., calculations or general greetings).
- **Exact Source Citations**: Every document-supported answer displays clear source reference badges (`Source: Company_Leave_Policy.pdf — Page 1`).
- **Grounded Non-Hallucination**: If the uploaded PDFs do not contain enough information, the agent explicitly states that the answer could not be found rather than making up details.
- **Multi-Turn Conversation Memory**: Tracks conversation history so follow-up queries work seamlessly (e.g., *"What is the leave policy?"* followed by *"How many days does it allow?"*).
- **Realistic Internal Tool UI**: Styled as a clean corporate utility without tacky AI hype animations or complex dashboards.

---

## 2. Basic Architecture

The project is structured modularly into decoupled layers:

| Component | File Path | Responsibilities |
| :--- | :--- | :--- |
| **Config** | [`backend/config.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/config.py) | Environment variables, API keys, storage directories, and chunking parameters. |
| **Ingestion** | [`backend/ingestion.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/ingestion.py) | Page-by-page text extraction from uploaded PDFs via `pypdf`. |
| **Chunking** | [`backend/chunking.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/chunking.py) | Recursive semantic text splitting with metadata preservation (`filename`, `page_number`). |
| **Embeddings** | [`backend/embeddings.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/embeddings.py) | Numerical vector generation using `sentence-transformers` (`all-MiniLM-L6-v2`). |
| **Vector Store** | [`backend/vector_store.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/vector_store.py) | Persistent vector storage and similarity search management via `ChromaDB`. |
| **RAG Tool** | [`backend/rag_tool.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/rag_tool.py) | Structured document search tool interface wrapped for the Agent. |
| **Agent Engine** | [`backend/agent.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/agent.py) | Intent evaluation, tool call decision, search query formulation, and grounded answer synthesis. |
| **API Server** | [`backend/app.py`](file:///Users/aashiyadav/Desktop/nhpc/backend/app.py) | FastAPI endpoints for PDF upload, listing documents, chat, and clearing storage. |
| **Frontend UI** | [`frontend/`](file:///Users/aashiyadav/Desktop/nhpc/frontend/) | Clean, responsive web client (`index.html`, `styles.css`, `app.js`). |

---

## 3. How RAG Works in This Project

Retrieval-Augmented Generation (RAG) combines semantic search with generative AI to ground answers in trusted private documents:

1. **Ingestion**: Uploaded PDFs are parsed page-by-page to retain document structure.
2. **Chunking**: Text is split into overlapping chunks (~600 characters with 100 character overlap) so semantic context is preserved across split boundaries.
3. **Embedding**: Each chunk is mapped to a 384-dimensional dense vector space using `all-MiniLM-L6-v2`.
4. **Vector Storage**: Vectors and metadata (`filename`, `page_number`, `chunk_id`) are stored in ChromaDB.
5. **Retrieval**: When a query is executed, its vector embedding is compared against indexed chunks via cosine similarity to fetch the top $K$ most relevant passages.
6. **Augmented Prompting**: The retrieved passages are injected into the LLM system prompt as strict reference material.

---

## 4. How the Agent Works

Unlike a standard passive RAG pipeline, this system uses an **Agentic decision loop**:

1. **Intent Analysis**: When the user sends a message, the Agent evaluates:
   - Does this query require information from internal company documents?
   - Is it a direct query (e.g., math calculation, greeting, or general question)?
2. **Contextual Query Reformulation**: If previous conversation history exists, the Agent reformulates ambiguous queries. For example, if the user asks *"How many days does it allow?"* after discussing the leave policy, the Agent formulates the search query as `"Leave policy allowed days"`.
3. **Tool Dispatch**: If document search is needed, the Agent dynamically invokes `search_pdf_knowledge_base`.
4. **Grounded Answer Generation**:
   - If relevant context is retrieved, the LLM generates a clear answer strictly backed by the text.
   - If retrieved context is insufficient or missing, the Agent responds that the information could not be found.
   - Sources are extracted and displayed as interactive tags below the response.

---

## 5. What Tools the Agent Has Access To

The agent has access to the **PDF Knowledge Base Retrieval Tool**:

- **Tool Name**: `search_pdf_knowledge_base`
- **Arguments**: `query` (str), `top_k` (int, default=4)
- **Output**: Formatted document passages accompanied by exact `filename` and `page_number` metadata.

---

## 6. How PDFs Are Processed

1. **Upload**: PDFs are uploaded via the drag-and-drop interface or API endpoint `/api/upload`.
2. **Extraction**: `pypdf.PdfReader` iterates over every page, extracting clean text alongside `filename`, `page_number`, and `total_pages`.
3. **Chunking**: `_recursive_text_split` partitions page text into manageable chunks.
4. **Indexing**: Chunks are embedded and stored in ChromaDB with persistent storage (`./chroma_db`).

---

## 7. How to Configure API Keys

The application supports both **Google Gemini** and **OpenAI** LLMs.

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and set your preferred API key:
   ```env
   # Set at least one API key:
   GEMINI_API_KEY=your_google_gemini_api_key_here
   # OR
   OPENAI_API_KEY=your_openai_api_key_here

   # Set provider choice: 'auto', 'gemini', or 'openai'
   LLM_PROVIDER=auto
   ```

*(Note: If no API key is provided, the application will still process PDFs, index vectors, evaluate tool routing, and display retrieved context snippets!)*

---

## 8. How to Install Dependencies

### Prerequisites:
- Python 3.10+ installed on your system.

### Installation Steps:

```bash
# 1. Create a virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# 3. Install required packages
pip install -r requirements.txt
```

---

## 9. How to Run the Application

### Option A: Run Server & Access Web UI

1. Start the FastAPI server using `uvicorn`:
   ```bash
   source .venv/bin/activate
   uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

### Option B: Generate Sample PDFs & Run Automated Tests

To test the system immediately with realistic sample PDF documents (Company Leave Policy & IT Security Guide):

```bash
# 1. Generate sample PDF files
python sample_data/generate_sample_pdfs.py

# 2. Run the end-to-end pipeline test
python test_pipeline.py
```

---

## 10. Why This Qualifies as an Agentic RAG Chatbot

Standard RAG implementations follow a fixed, linear pipeline: *User Input → Always Search Vector DB → Inject Context → Output*.

This application is **Agentic** because:
1. **Dynamic Tool Selection**: It actively reasons whether to search the vector database or answer directly based on query intent.
2. **Search Query Synthesis**: It does not just blindly pass raw user input to vector search; it reformulates search queries using conversation context to resolve coreferences (e.g. "it", "that policy").
3. **Grounded Fallback Execution**: It evaluates the quality of retrieved passages and chooses between synthesizing a grounded answer or triggering an explicit "information not found" fallback.
