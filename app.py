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
PROMPT_CONFIG_PATH = "prompts.json"

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
    # if not api_key:
    #     raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set")

    payload = await request.json()
    job_posting_url = payload.get("job_posting_url")
    if not job_posting_url:
        raise HTTPException(status_code=400, detail="job_posting_url required")
    resume_url = DEFAULT_RESUME_URL

    try:
        def work():
            # resume = Resume.from_pdf_url(api_key, resume_url, PROMPT_CONFIG_PATH)
            # suggestion = resume.generate_suggestions(job_posting_url)
            # return asdict(suggestion)

            # Return mock data from previous query
            import json
            with open("example_output.json", "r") as f:
                return json.load(f)

        result = await asyncio.to_thread(work)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
async def generate(request: Request):
    """Generate a new resume using suggestion data sent from the client.

    For now this is a placeholder that returns a mock generated resume URL.
    """
    payload = await request.json()
    suggestion = payload.get("suggestion") or payload.get("suggestions")
    if not suggestion:
        raise HTTPException(status_code=400, detail="suggestion payload required")

    try:
        def work():
            # TODO: integrate real resume generation here. For now return a mock URL.
            return {"generated_resume_url": DEFAULT_RESUME_URL, "status": "ok"}

        result = await asyncio.to_thread(work)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
