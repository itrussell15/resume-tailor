from __future__ import annotations

import os
import datetime
from pydoc import resolve

import httpx
import json
import requests
from google import genai
from google.genai import types
from dataclasses import dataclass, asdict

CONFIG = "context.json"
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

class Resume:

    def __init__(self, api_key: str, resume_context: types.Part) -> None:
        self._client = genai.Client(api_key=api_key)
        self._resume_context = resume_context

    @classmethod
    def from_pdf_url(self, api_key: str, url: str) -> Resume:
        pdf_data = httpx.get(url).content
        resume_context = types.Part.from_bytes(
            data=pdf_data,
            mime_type='application/pdf',
        )
        return Resume(api_key, resume_context)

    def generate_suggestions(self, job_posting_url: str) -> ResumeSuggestions:
        job_posting_data = self._fetch_job_posting_contents(job_posting_url)
        job_insights = self._mine_job_insights(job_posting_data)

        header = "POTENTIALLY HELPFUL THINGS"
        split_char = "$$$"

        prompt = f"Using the job posting and information and the information section in the resume, tailor the resume data to match the information that is found in the job posting. Keep this information concise and able to fit in the same amount of space that the original information fit in already. For each job, please provide at most 4 bullet points that highlight the skills that the current resume has, but in a way that the new job poster would be interested in. Do not make up content about what the user has done ever. Only use the information that you have available here. Please do not include things in your response that will not change based on the job posting information like a person's name or email, only include information that can or could have changed based on the job posting you have been shown. If you feel that more information about the person could greatly help you add content about them to increase their success when applying for this job, please leave a note about what you would like to know or what things they might be able to add that could help their changes, if you do this then add it as a section at the very top titled '{header}' end it with '{split_char}'. For uniformity, please always include this section and leave it blank if you don't have any insights."
        response = self._client.models.generate_content(
            model=MODEL,
            contents=[
                self._resume_context,
                job_insights,
                prompt
            ]
        )

        suggestions, updated_content = response.text.split(split_char)
        return ResumeSuggestions(
            query_timestamp=datetime.datetime.now().strftime(TIMESTAMP_FORMAT),
            job_posting_url=job_posting_url,
            job_posting_insights=job_insights.text,
            suggestion_prompt=prompt,
            suggestion_content=suggestions.split(header)[-1].strip(),
            revised_resume_content=updated_content.strip(),
            model=MODEL
        )

    def _mine_job_insights(self, raw_job_data: str) -> types.Part:
        prompt="Look through this job posting content and extract relevant information. Content will likely be in raw html. Find information that someone who might be looking to apply to this job would want to know about specific qualifications that they should have, experience level, etc."
        response = self._client.models.generate_content(
            model=MODEL,
            contents=[
                raw_job_data,
                prompt
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
    resume = Resume.from_pdf_url(api_key, url)
    suggestion = resume.generate_suggestions(job_url)

    final = os.path.join(output, f"{suggestion.query_timestamp}.json")
    with open(final, 'w') as f:
        json.dump(asdict(suggestion), f, indent=3)

    print(f"Suggestions: {suggestion.suggestion_content}")
    print(f"New Resume: \n{suggestion.revised_resume_content}")




