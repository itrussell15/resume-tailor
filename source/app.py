from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import logging
import asyncio
from dataclasses import asdict

from .generate_contents import Resume, ResumeSuggestions

logger = logging.getLogger("uvicorn.app")

app = FastAPI()
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# TODO Move these to config file or environment variables
INDEX_PATH = os.path.join(static_dir, "index.html")
DEFAULT_RESUME_URL = "https://resume.itrussell.me/docs/resume.pdf"
PROMPT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(static_dir)), "resources", "prompts.json")

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
    resume_url = DEFAULT_RESUME_URL
    logger.info(f"Incoming request for posting from {job_posting_url}")

    try:
        def work():
            resume = Resume.from_pdf_url(api_key, resume_url, PROMPT_CONFIG_PATH)
            suggestion = resume.generate_suggestions(job_posting_url)
            logger.info(f"Generated suggestion: {suggestion} - {suggestion.suggestion_content.job_details}")
            output_name = suggestion.suggestion_content.job_details.file_name
            return output_name, asdict(suggestion)

            # # Return mock data from previous query
            # formatted_data = ResumeSuggestions.from_json_file("example_output.json")
            # return formatted_data.suggestion_content.job_details.file_name, asdict(formatted_data)

        save_name, result = await asyncio.to_thread(work)
        output_path = os.path.join(os.path.dirname(os.path.dirname(PROMPT_CONFIG_PATH)), "output",f"{save_name}.json")
        logger.info(f"Saving suggestion output to {output_path}")
        with open(output_path, "w") as f:
            json.dump(result, f, indent=4)
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
