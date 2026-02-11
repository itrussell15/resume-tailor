# Resume_Automater - FastAPI frontend

Quick start (local):

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Export your Google GenAI API key:

```bash
export GOOGLE_API_KEY="<your_key>"
```

3. Run the app:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

4. Open http://localhost:8000 and paste a job posting URL.

Docker build & run:

```bash
docker build -t resume-automater .
docker run -e GOOGLE_API_KEY="$GOOGLE_API_KEY" -p 8000:8000 resume-automater
```

Notes:
- The app will fetch the resume PDF and job posting URL; ensure network access.
- SECRET.txt is deprecated for the web app; use `GOOGLE_API_KEY` environment variable.
- For production, consider running with a process manager and adding request timeouts or background job handling.
