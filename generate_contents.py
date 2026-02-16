from __future__ import annotations

import os
import json
import logging
import datetime
from pydoc import resolve

import httpx
import json
import requests
from google import genai
from google.genai import types
from dataclasses import dataclass, asdict

from typing import List, Dict, Any

MODEL = "gemini-3-flash-preview"
TIMESTAMP_FORMAT = "%Y_%m_%d-%H_%M_%S"

@dataclass
class JobDetails:
    role: str
    company: str

@dataclass
class JobBlock:
    company: str
    bullet_points: List[str]

@dataclass
class ResumeFormattedResponse:
    job_details: JobDetails
    missing_skill: str
    resume_changes: List[JobBlock]

@dataclass 
class PromptConfig:
    missing_skill: str
    resume_changes: str
    job_info_scrape: str
    insight_extraction: str

    @staticmethod
    def from_json(path: str) -> PromptConfig:
        if not os.path.exists(path):
            raise FileNotFoundError(f"No file '{path}' found.")

        with open(path, "r") as f:
            json_data = json.load(f)
        output = PromptConfig(**json_data["prompts"])
        return output

@dataclass
class ResumeSuggestions:
    query_timestamp: datetime.datetime
    job_posting_url: str
    job_posting_insights: str
    prompts: PromptConfig
    suggestion_content: ResumeFormattedResponse
    model: str

    @staticmethod
    def from_response(response: str) -> None:
        job_details = JobDetails(**response["job_details"])

class Resume:

    def __init__(self, api_key: str, resume_context: types.Part, prompt_config: PromptConfig) -> None:
        self._client = genai.Client(api_key=api_key)
        self._resume_context = resume_context
        self._prompts = prompt_config

    @staticmethod
    def from_pdf_url(api_key: str, url: str, prompt_config_path: str) -> Resume:
        pdf_data = httpx.get(url).content
        resume_context = types.Part.from_bytes(
            data=pdf_data,
            mime_type='application/pdf',
        )
        prompts = PromptConfig.from_json(prompt_config_path)
        return Resume(api_key, resume_context, prompts)

    def generate_suggestions(self, job_posting_url: str) -> ResumeSuggestions:
        job_posting_data = self._fetch_job_posting_contents(job_posting_url)
        job_insights = self._mine_job_insights(job_posting_data)

        system_instruction = "You are to generate response in json format that would correspond to each section. Do not wrap this json as a markdown, simply just json format as a string"
        response = self._client.models.generate_content(
            model=MODEL,
            contents=[
                self._resume_context,
                job_insights,
                self._prompts.job_info_scrape,
                self._prompts.missing_skill,
                self._prompts.resume_changes,
            ]
        )

        out_response = response.text.strip()
        json_response = None
        try: 
            json_response = json.loads(out_response.strip())
        except json.JSONDecodeError as e:
            # It likes to response with markdown formatting. 
            # Like ```json Content ``` so we have to try and parse out the json from the markdown if the first attempt fails.
            try: 
                split_string = out_response.split("\n")[1:-1]
                json_response = json.loads("\n".join(split_string))
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {out_response}")
                raise e

        return ResumeSuggestions(
            query_timestamp=datetime.datetime.now().strftime(TIMESTAMP_FORMAT),
            job_posting_url=job_posting_url,
            job_posting_insights=job_insights.text,
            prompts=self._prompts,
            suggestion_content=ResumeFormattedResponse(**json_response),
            model=MODEL
        )

    def _mine_job_insights(self, raw_job_data: str) -> types.Part:
        response = self._client.models.generate_content(
            model=MODEL,
            contents=[
                raw_job_data,
                self._prompts.insight_extraction
            ]
        )
        return types.Part(response.text)

    def _fetch_job_posting_contents(self, url: str) -> str:
        r = requests.get(url)
        if not r.ok:
            raise ConnectionError(f"{r.status_code} return code - Unable to fetch url: {url}.")
        return r.text

if __name__ == "__main__":
    output = os.path.join("output")

    with open("SECRET.txt", "r") as f:
        api_key = f.readlines()[0].strip()

    url = "https://resume.itrussell.me/docs/resume.pdf"
    job_url = "https://www.linkedin.com/jobs/view/4341275216"
    prompt_path = "prompts.json"

    resume = Resume.from_pdf_url(api_key, url, prompt_path)
    suggestion = resume.generate_suggestions(job_url)
    print(suggestion)

    with open("output.json", 'w') as f:
        json.dump(asdict(suggestion), f, indent=4)



