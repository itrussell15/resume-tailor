from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio
from dataclasses import asdict

from generate_contents import Resume

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

INDEX_PATH = os.path.join("static", "index.html")
DEFAULT_RESUME_URL = "https://resume.itrussell.me/docs/resume.pdf"

@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open(INDEX_PATH, "r") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="UI not found")

@app.post("/api/suggestions")
async def suggestions(request: Request):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set")

    payload = await request.json()
    job_posting_url = payload.get("job_posting_url")
    if not job_posting_url:
        raise HTTPException(status_code=400, detail="job_posting_url required")
    resume_url = payload.get("resume_pdf_url") or DEFAULT_RESUME_URL

    try:
        def work():
            resume = Resume.from_pdf_url(api_key, resume_url)
            suggestion = resume.generate_suggestions(job_posting_url)
            return asdict(suggestion)

        result = await asyncio.to_thread(work)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
