from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import logging
from pathlib import Path
import requests

import asyncio
from dataclasses import dataclass, asdict

from gotenberg_client import GotenbergClient

from .log_utils import setup_logging, get_logger
from .generate_contents import Resume, ResumeSuggestions
from .doc_modifier import DocModifier

@dataclass
class Config:

    prompt_path: str
    pdf_resume_url: str
    docx_resume_template_path: str
    output: str

    @staticmethod
    def from_json_file(path: str) -> Config:
        if not os.path.exists(path):
            raise FileExistsError(path)
        with open(path) as f:
            data = json.load(f)
        return Config(**data)

setup_logging()
logger = get_logger(__name__)

app = FastAPI()

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

CONFIG = Config.from_json_file(os.path.join("resources", "config.json"))

@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open(os.path.join(static_dir, "index.html"), "r") as f:
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
    logger.info(f"Incoming request for posting from {job_posting_url}")

    try:
        def work():
            # resume = Resume.from_pdf_url(api_1tion)

            # Return mock data from previous query
            formatted_data = ResumeSuggestions.from_json_file("example_output.json")
            return formatted_data.suggestion_content.job_details.file_name, asdict(formatted_data)

        save_name, result = await asyncio.to_thread(work)
        output_path = os.path.join(CONFIG.output, "json", f"{save_name}.json")
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
            formatted_suggestion = ResumeSuggestions.from_json(suggestion)
            template_docx = DocModifier(CONFIG.docx_resume_template_path)
            template_docx.modify_sections(formatted_suggestion.suggestion_content.resume_changes)

            # Save docx
            output_docx_path = os.path.join(CONFIG.output, "docx", f"{formatted_suggestion.suggestion_content.job_details.file_name}.docx")
            template_docx.save(output_docx_path)
            logger.info(f"Docx resume saved to {output_docx_path}")

            # # Save pdf
            output_pdf_path = os.path.join(CONFIG.output, "pdf", f"{formatted_suggestion.suggestion_content.job_details.file_name}.pdf")
            is_ok = create_pdf_from_docx(output_path=output_pdf_path, input_path=output_docx_path)
            # is_ok = True
            
            return {"success": True, "status": "ok"}

        result = await asyncio.to_thread(work)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error generating resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_pdf_from_docx(output_path: str, input_path: str): 
    if not os.path.exists(input_path):
        raise FileExistsError(f"No file found: {input_path}")
    
    input_type = os.path.splitext(input_path)[-1]
    if input_type != ".docx":
        raise TypeError(f"{input_path} is not .docx, found {input_type}")

    output_type = os.path.splitext(output_path)[-1]
    if output_type != ".pdf":
        raise TypeError(f"{output_path} is not .pdf, found {output_type}")
    
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        logger.info(f"No output folder: {output_dir}, creating now.")
        os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Converting to pdf from '{input_path}'")

    # TODO Add this to env variable or config
    gotenberg_url = "https://demo.gotenberg.dev"
    input_path = Path(input_path)
    output_path = Path(output_path)

    with GotenbergClient(gotenberg_url) as client:
        with client.libre_office.to_pdf() as route:
            try:
                response = route.convert(input_path).run()
                response.to_file(output_path)
                return True
            except Exception as e:
                logger.warning(f"gotenberg client conversion failed: {e}")