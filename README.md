# INGRES RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot specifically designed for the INGRES (Integrated Groundwater Resource Information System) platform. This system provides intelligent question-answering capabilities for groundwater resources data in India.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │    MongoDB      │    │  FAISS Vector  │
│   Backend       │◄──►│   Database      │    │     Store      │
│                 │    │                 │    │                 │
│ • Query Router  │    │ • Structured    │    │ • Text          │
│ • Entity Extract│    │   Groundwater   │    │   Embeddings    │
│ • Context Build │    │   Data          │    │ • Semantic      │
│ • LLM Generate  │    │ • Metadata      │    │   Search        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ✨ Features

- **Multi-Modal RAG**: Combines structured (CSV/Excel) and unstructured (PDF/HTML) data
- **Entity Extraction**: Automatically identifies states, metrics, and years from queries
- **Intent Classification**: Understands query types (comparison, statistics, help, etc.)
- **Semantic Search**: FAISS-powered vector similarity search
- **Fallback Responses**: Works even without OpenAI API key
- **Real-time Processing**: Async FastAPI backend for high performance
- **Feedback System**: User rating and comment collection
- **Comprehensive Sources**: Provides data provenance for all responses

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env` and update with your settings:

```bash
cp .env.example .env
```

Edit `.env`:
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ingres_rag
GEMINI_API_KEY=your_gemini_api_key_here  # Optional
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
TOP_K_RESULTS=5
```

### 3. Start MongoDB

Make sure MongoDB is running:
```bash
# macOS (with Homebrew)
brew services start mongodb/brew/mongodb-community

# Linux (systemd)
sudo systemctl start mongod

# Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 4. Run the System

```bash
python run.py
```

The system will:
- ✅ Initialize database indexes
- 📚 Process all data files in the `data/` directory  
- 🔍 Build vector embeddings
- 🚀 Start the FastAPI server at `http://localhost:8000`

### 5. Access the System

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Simple Frontend**: Open `frontend/index.html` in your browser

## 📁 Project Structure

```
sih_2025/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── models.py            # Pydantic data models
│   ├── database.py          # MongoDB operations
│   ├── vector_store.py      # FAISS vector operations
│   ├── preprocessor.py      # Data processing pipeline
│   └── rag_engine.py        # Query processing and RAG logic
├── data/
│   ├── raw/
│   │   ├── website_texts/   # HTML files (FAQs, etc.)
│   │   └── report_pdfs/     # PDF documents
│   └── structure_tables/    # CSV/Excel groundwater data
├── frontend/
│   └── index.html           # Simple web interface
├── requirements.txt
├── .env                     # Environment configuration
├── run.py                   # System startup script
└── README.md
```

## 🔧 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query` | Process user queries and return AI responses |
| `POST` | `/feedback` | Store user feedback on responses |
| `GET` | `/health` | System health and statistics |
| `GET` | `/stats` | Detailed system metrics |

### Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/search/structured` | Query structured groundwater data |
| `GET` | `/search/unstructured` | Semantic search through documents |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reprocess-data` | Reprocess all data files |

## 💬 Usage Examples

### Query Examples

```json
POST /query
{
    "query": "What is the rainfall data for Maharashtra?",
    "session_id": "optional-session-id",
    "user_id": "optional-user-id"
}
```

**Response:**
```json
{
    "answer": "Based on the available data, Maharashtra has a rainfall of 855.95 mm with groundwater extraction of...",
    "sources": [
        {
            "type": "structured",
            "source": "INGRES Database",
            "content": "Groundwater data for Maharashtra"
        }
    ],
    "confidence_score": 0.85,
    "response_time": 1.23
}
```

### Sample Queries

- "Which states have the highest groundwater extraction?"
- "How do I upload shapefile in INGRES?"
- "Compare rainfall between Gujarat and Rajasthan"
- "What is the annual extractable groundwater resources for Bihar?"
- "Explain the process of groundwater recharge calculation"

## 🎯 System Components

### 1. Data Preprocessor (`preprocessor.py`)

- **Structured Data**: Processes CSV/Excel files with groundwater statistics
- **Unstructured Data**: Extracts text from PDFs and HTML files
- **Text Chunking**: Splits long documents for better retrieval
- **Metadata Extraction**: Preserves source information and context

### 2. Vector Store (`vector_store.py`)

- **Embedding Model**: Sentence-BERT for text embeddings
- **FAISS Index**: Efficient similarity search
- **Persistence**: Saves/loads indexes to disk
- **Semantic Search**: Finds contextually relevant information

### 3. Query Processor (`rag_engine.py`)

- **Entity Extraction**: Identifies states, metrics, years
- **Intent Classification**: Determines query type and approach
- **Multi-Source Retrieval**: Combines structured and unstructured data
- **Context Building**: Merges relevant information
- **LLM Integration**: Uses OpenAI GPT for response generation
- **Fallback Logic**: Template-based responses when AI is unavailable

### 4. Database Manager (`database.py`)

- **MongoDB Integration**: Async operations with Motor
- **Structured Storage**: Groundwater statistics with indexing
- **Session Management**: Chat history and user tracking
- **Feedback Collection**: User ratings and comments

## 🛠️ Development

### Adding New Data Sources

1. Place files in appropriate directories:
   - Structured: `data/structure_tables/`
   - Unstructured: `data/raw/`

2. Reprocess data:
   ```bash
   curl -X POST http://localhost:8000/reprocess-data
   ```

### Customizing the RAG Pipeline

The RAG pipeline can be customized by modifying:

- **Entity Patterns** (`rag_engine.py`): Add new entity types
- **Intent Classification** (`rag_engine.py`): Define new query intents  
- **Data Processors** (`preprocessor.py`): Support new file formats
- **Vector Store** (`vector_store.py`): Change embedding models

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `DATABASE_NAME` | `ingres_rag` | Database name |
| `GEMINI_API_KEY` | - | Google Gemini API key (optional) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `VECTOR_DIMENSION` | `384` | Embedding dimensions |
| `TOP_K_RESULTS` | `5` | Number of similar documents to retrieve |

## 📊 Monitoring and Analytics

### Health Check Response

```json
GET /health
{
    "status": "healthy",
    "timestamp": "2025-09-26T10:30:00Z",
    "components": {
        "vector_store": {
            "status": "healthy",
            "stats": {
                "total_documents": 1250,
                "index_size": 1250,
                "embedding_dimension": 384
            }
        },
        "data_processor": {
            "status": "healthy",
            "stats": {
                "csv_files": 1,
                "excel_files": 6,
                "html_files": 1,
                "pdf_files": 1
            }
        }
    }
}
```

### System Statistics

```json
GET /stats
{
    "vector_store": {
        "total_documents": 1250,
        "model_name": "all-MiniLM-L6-v2"
    },
    "data_processing": {
        "structured_files": {"csv_files": 1, "excel_files": 6},
        "unstructured_files": {"html_files": 1, "pdf_files": 1}
    }
}
```

## 🚨 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   ```
   Ensure MongoDB is running and accessible at the configured URL
   ```

2. **No Data Found**
   ```
   Check that data files exist in data/ directory
   Run reprocessing: POST /reprocess-data
   ```

3. **Vector Store Issues**
   ```
   Delete existing FAISS files and restart:
   rm -rf data/faiss_index.bin data/documents.pkl
   python run.py
   ```

4. **Gemini API Errors**
   ```
   System will work with fallback responses if API key is missing
   Check API key validity and rate limits
   ```

## 🔮 Future Enhancements

- **Multi-language Support**: Hindi and regional language queries
- **Advanced Analytics**: Query pattern analysis and optimization
- **Real-time Data Integration**: Live groundwater monitoring feeds
- **Voice Interface**: Speech-to-text query processing
- **Advanced Visualizations**: Interactive charts and maps
- **Mobile App**: React Native or Flutter mobile interface

## 📝 License

This project is developed for the Smart India Hackathon 2025. Please refer to the competition guidelines for usage terms.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📧 Support

For technical support and questions, please create an issue in the repository or contact the development team.

---

**Built with ❤️ for groundwater resource management in India** 🇮🇳