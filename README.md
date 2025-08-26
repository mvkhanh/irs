# HCMAI2025

A FastAPI-based AI application powered by Milvus for vector search, MongoDB for metadata storage, and MinIO for object storage.

## 🧑‍💻 Getting Started

### Prerequisites
- Docker
- Docker Compose
- Python 3.10
- uv

### Download the dataset
1. [Metadata](https://drive.google.com/drive/folders/1vghRbevk8KtosbTIJeHyXr3KoojZxh2Z?usp=sharing), follow the guide.ipynb and example data folder in here.
2. [Keyframes](https://docs.google.com/spreadsheets/d/1PGE28vdyZVfOBW85PqwY3rcYZVGXEI_wL4a8Ci-c4Gk/edit?gid=0#gid=0), just the keyframes and objects batch 1 for testing.



### 🔧 Local Development
1. Clone the repo and start all services:
```bash
git clone https://github.com/yourusername/aio-aic.git
cd aio-aic
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

(http://localhost:8000/keyframe/)