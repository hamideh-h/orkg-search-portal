# ORKG Search (Step 1)

Minimal FastAPI backend that queries ORKG resources by title/label.

## Setup
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

## Run
uvicorn app.main:app --reload

Then open:
- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/docs  (Swagger UI)
- Example: http://127.0.0.1:8000/api/search?q=software&size=10&page=0
