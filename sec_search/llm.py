import json
import logging
import os
from functools import lru_cache
from typing import Optional

import vertexai
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from vertexai.generative_models import GenerativeModel


@lru_cache(maxsize=1)
def init_vertaxai() -> None:
    gcp_project_id = os.environ.get("GCP_PROJECT_ID")
    gcp_region = os.environ.get("GCP_REGION", "us-central1")
    vertexai.init(project=gcp_project_id, location=gcp_region)


def pick_match_with_llm(fund_name: str, search_result: list | None):
    if not search_result:
        return None

    prompt = _pick_fund_prompt(fund_name, search_result)
    response = _ask_model("gemini-1.5-flash-002", prompt)
    if response:
        return _remove_md_json_wrapper(response)
    else:
        return None


def _ask_model(model: str, prompt: str) -> Optional[str]:
    if model.startswith("gemini"):
        return _chat_with_gemini(model, prompt)
    else:
        raise ValueError(f"Unknown model: {model}")


def _pick_fund_prompt(fund_name: str, search_result: list) -> str:
    unique_funds = set()
    fund_list = []

    for row in search_result:
        fund_entry = f"{row[5]}, {row[0]}"
        if fund_entry not in unique_funds:
            unique_funds.add(fund_entry)
            fund_list.append(fund_entry)

    return f"""
I have this fund table which consists of 2 columns, fund name and CIK.
==begin table==
{"\n".join(fund_list)}
==end table==

please tell me which row whose fund name column is the closest match to

'{fund_name}'

use the following format for output:
{{"fund_name": "<fund_name_from_table", "cik": "<cik_from_table>"}}
"""


def _remove_md_json_wrapper(response: str) -> str | None:
    # the response should be a JSON
    # sometimes Gemini wraps it in a markdown block ```json ...```
    # so we unrap the markdown block and get to the json
    if len(response) > 20:
        json_str = response.strip()
        start_markdown_index = response.find("```json")
        end_markdown__index = response.rfind("```")
        if start_markdown_index >= 0 and end_markdown__index >= 0:
            json_str = response[start_markdown_index + 7 : end_markdown__index]

        try:
            json.loads(json_str)  # just to test if the json is valid
            return json_str
        except json.JSONDecodeError:
            print("Failed to parse JSON from response")

    return response


@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=1, min=4, max=120),
    retry=retry_if_exception_type(ResourceExhausted),
)
def _chat_with_gemini(model_name: str, prompt: str) -> Optional[str]:
    try:
        init_vertaxai()
        model = GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 1024,
                "temperature": 0,
                "top_p": 0.95,
            },
        )
        return response.text
    except ResourceExhausted:
        # for tenacity to retry
        raise
    except Exception as e:
        logging.warning(f"Error calling Gemini API: {type(e)},{str(e)}")
        return None
