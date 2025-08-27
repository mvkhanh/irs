# Video retrieval system

A FastAPI-based AI application powered by Milvus for vector search, MongoDB for metadata storage, and MinIO for object storage. It supports text-embedding search, OCR, ASR, object-based filtering, image search, group/video ID lookup, and multi-modal query combinations.

## 🧑‍💻 Getting Started

### Prerequisites
- Docker
- Docker Compose
- Python 3.10
- uv

### 🔧 Local Development
1. Clone the repo and start all services:
```bash
git clone https://github.com/mvkhanh/irs.git
cd irs
```

2. Install uv and setup env
```bash
pip install uv
uv init --python=3.10
uv add aiofiles beanie dotenv fastapi[standard] google-generativeai httpx ipykernel jinja2 langdetect llama-index llama-index-llms-google-genai motor nicegui numpy open-clip-torch pydantic-settings pymilvus torch typing-extensions usearch uvicorn deep-translator
```

3. Activate .venv
```bash
source .venv/bin/activate
```
4. Run docker compose
```bash
docker compose up -d
```

4. Data Migration 
```bash
python migration/embedding_migration.py --file_path <clip-features-32.pt file>
python migration/keyframe_migration.py --file_path <clip_idmap.json file path> --object_folder <objects folder path> --caption_folder <asr folder path>
```

5. Run the application

```bash
cd app
python main.py
```
