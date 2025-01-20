import os
import re
import time

from bs4 import BeautifulSoup
from loguru import logger
import requests


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "Accept-Encoding": "*",
        "Connection": "keep-alive"
    }


def desired_url_pattern(url_to_check: str):
    """Check if the URL matches the desired pattern."""
    return "/demokrati/politik/byraadet/spoergsmaal-fra-byraadets-medlemmer/spoergsmaal-fra-byraadets-medlemmer" in url_to_check


def download_pdf(yearly_dir: str, url: str):
    """Download a PDF from a URL and save it using the unique ID contained in the URL as its filename."""
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    match = re.search(r'\/media\/(.+)\/(.+)\.pdf', url)
    unique_id = match.group(1)
    filename = match.group(2)
    target_file = os.path.join(yearly_dir, f"{filename}_{unique_id}.pdf")
    with open(target_file, "wb") as file:
        file.write(response.content)


def main():
    base_url = "https://aarhus.dk/demokrati/politik/byraadet/spoergsmaal-fra-byraadets-medlemmer"
    response = requests.get(base_url, headers=get_headers())
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract links to yearly questions
    year_links = [
        f"https://aarhus.dk/{anchor['href']}"
        for anchor in soup.find_all("a", class_="link-box link-box__article")
        if desired_url_pattern(anchor["href"])
    ]

    for year_link in year_links[1:]:
        logger.info(f'Processing {year_link}')
        yearly_dir = year_link.split('/')[-1]
        os.makedirs(yearly_dir, exist_ok=True)
        year_response = requests.get(year_link, headers=get_headers())
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
        api_response = requests.get(api_url, params=request_data, headers=get_headers())
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
            question_dir = question_link.split('/')[-1]
            target_dir = os.path.join(yearly_dir, question_dir)
            os.makedirs(target_dir, exist_ok=True)
            question_response = requests.get(question_link, headers=get_headers())
            question_response.raise_for_status()
            question_soup = BeautifulSoup(question_response.text, "html.parser")

            # Extract and download associated documents
            documents = question_soup.select(".list__downloads .list__link")
            for document in documents:
                time.sleep(2)  # Be polite with requests to avoid resetting the connection
                download_url = f"https://aarhus.dk{document.get('href')}"  # noqa: E231
                logger.info(f'Downloading from URL: {download_url}')
                download_pdf(target_dir, download_url)


if __name__ == "__main__":
    main()
