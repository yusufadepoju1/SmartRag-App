#  SmartRag

SmartRag is a general-purpose RAG (Retrieval-Augmented Generation) application that allows anyone to upload and query any type of document using advanced AI.

##  Features

-  Upload and process any document (PDF, DOCX, TXT, etc.)
-  Ask questions and get intelligent answers from your documents
-  Built on top of RAG (Retrieval-Augmented Generation) logic
-  Simple, extensible architecture
-  Designed for anyone — no technical knowledge required

##  How It Works

1. **Upload** a document.
2. **Index** and store document chunks in a vector database.
3. **Ask** a question in natural language.
4. **Retrieve** relevant chunks and generate an answer using an LLM.

##  Tech Stack

- Python
- FastAPI
- LangChain
- FAISS (or Chroma for vector storage)
- OpenAI / LLM of choice

##  Getting Started

### 1. Clone the Repo

```bash
git clone https://github.com/yourusername/smartrag.git
cd smartrag
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

Create a `.env` file and add your API keys:

```env
OPENAI_API_KEY=your_openai_key
```

### 4. Run the App

```bash
uvicorn app:app --reload
```

Then go to `http://localhost:8000/docs` to use the Swagger UI.

##  Example Use Cases

- Reading legal documents and asking questions
- Summarizing lengthy PDFs
- Quickly extracting insights from business reports
- Personal study assistant for any subject

##  Folder Structure

```
.
├── app.py
├── rag_logic.py
├── vector_store/
├── documents/
└── README.md
```

##  Contributions

Feel free to open issues or submit pull requests. Ideas and improvements are welcome!

##  Inspired by

Projects like LangChain, GPT Index, and many others in the RAG ecosystem.

![SmartRag App Mockup](assets/Screenshot (156).png)
