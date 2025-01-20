# TODO: generate requirements.txt

import os
import secrets
import time

from bs4 import BeautifulSoup
from loguru import logger
import requests


def desired_url_pattern(url_to_check: str):
    """Check if the URL matches the desired pattern."""
    return "/demokrati/politik/byraadet/spoergsmaal-fra-byraadets-medlemmer/spoergsmaal-fra-byraadets-medlemmer" in url_to_check


def download_pdf(yearly_dir: str, url: str):
    """Download a PDF from a URL and save it with a random filename."""
    response = requests.get(url)
    response.raise_for_status()
    target_file = os.path.join(yearly_dir, f"{secrets.token_hex(5)}.pdf")
    with open(target_file, "wb") as file:
        file.write(response.content)


def main():
    base_url = "https://aarhus.dk/demokrati/politik/byraadet/spoergsmaal-fra-byraadets-medlemmer"

    # Get the main page content
    response = requests.get(base_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract links to yearly questions
    year_links = [
        f"https://aarhus.dk/{anchor['href']}"
        for anchor in soup.find_all("a", class_="link-box link-box__article")
        if desired_url_pattern(anchor["href"])
    ]

    for year_link in year_links:
        logger.info(f'Processing {year_link}')
        yearly_dir = year_link.split('/')[-1]
        os.makedirs(yearly_dir, exist_ok=True)
        year_response = requests.get(year_link)
        year_response.raise_for_status()
        year_soup = BeautifulSoup(year_response.text, "html.parser")

        # Extract the page ID for API requests
        page_id = year_soup.find("meta", {"name": "pageId"}).get("content")
        request_data = {
            "pageId": page_id,
            "dontsortbydate": "False",
            "page": 1,
            "pageSize": 1000,  # Note: If we have more than 1000 questions in a given year, we will not retrieve all questions (this has so far not been the case...)
            "year": "",
            "month": "",
            "tag": "",
            "lang": "da",
            "showDate": "True",
        }

        # Fetch the API response
        api_url = "https://aarhus.dk/umbraco/surface/list/PaginationListItem"
        api_response = requests.get(api_url, params=request_data)
        api_response.raise_for_status()
        api_soup = BeautifulSoup(api_response.text, "html.parser")

        # Extract links to individual questions
        question_links = [
            f"https://aarhus.dk/{anchor['href']}"
            for anchor in api_soup.find_all("a")
            if desired_url_pattern(anchor["href"])
        ]

        for question_link in question_links:
            logger.info(question_link)
            time.sleep(2)  # Be polite with requests to avoid resetting the connection
            question_response = requests.get(question_link)
            question_response.raise_for_status()
            question_soup = BeautifulSoup(question_response.text, "html.parser")

            # Extract and download associated documents
            documents = question_soup.select(".list__downloads .list__link")
            for document in documents:
                download_url = f"https://aarhus.dk{document.get('href')}"  # noqa: E231
                logger.info(f'Downloading from URL: {download_url}')
                download_pdf(yearly_dir, download_url)


if __name__ == "__main__":
    main()
