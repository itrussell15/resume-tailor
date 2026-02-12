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

MODEL = "gemini-3-flash-preview"
TIMESTAMP_FORMAT = "%Y_%m_%d-%H_%M_%S"

@dataclass
class ResumeSuggestions:
    query_timestamp: datetime.datetime
    job_posting_url: str
    job_posting_insights: str
    suggestion_prompt: str
    suggestion_content: str
    revised_resume_content: str
    model: str


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

        system_instruction = "You are to generate response in json format that would correspond to each section"
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
        return response

        # suggestions, updated_content = response.text.split(split_char)
        # return ResumeSuggestions(
        #     query_timestamp=datetime.datetime.now().strftime(TIMESTAMP_FORMAT),
        #     job_posting_url=job_posting_url,
        #     job_posting_insights=job_insights.text,
        #     suggestion_prompt=prompt,
        #     suggestion_content=suggestions.split(header)[-1].strip(),
        #     revised_resume_content=updated_content.strip(),
        #     model=MODEL
        # )

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
    job_url = "https://www.linkedin.com/jobs/view/4322330173"
    prompt_path = "prompts.json"

    resume = Resume.from_pdf_url(api_key, url, prompt_path)
    suggestion = resume.generate_suggestions(job_url)
    print(suggestion.text)

    final = os.path.join(output, f"test.json")
    with open(final, 'w') as f:
        data = json.loads(suggestions.text)
        json.dump(data, f, indent=3)

    # print(f"Suggestions: {suggestion.suggestion_content}")
    # print(f"New Resume: \n{suggestion.revised_resume_content}")




