import os
import re

from bs4 import BeautifulSoup
from loguru import logger
import requests


def get_headers():
    """Return headers for HTTP requests."""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "Accept-Encoding": "*",
        "Connection": "keep-alive",
    }


# fmt: off
def is_desired_url(url: str) -> bool:
    """Check if the URL matches the desired pattern."""
    return "/demokrati/politik/byraadet/spoergsmaal-fra-byraadets-medlemmer/spoergsmaal-fra-byraadets-medlemmer" in url
# fmt: on


def download_file(directory: str, url: str):
    """Download a file from a URL and save it in the specified directory."""
    response = requests.get(url, headers=get_headers(), timeout=10)
    response.raise_for_status()

    match = re.search(r"\/media\/(.+)\/(.+)\.(.+)\?", url)

    unique_id, filename, extension = match.groups()  # type: ignore
    target_file = os.path.join(directory, f"{filename}_{unique_id}.{extension}")

    with open(target_file, "wb") as file:
        file.write(response.content)

    logger.info(f"Downloaded file: {target_file}")


def process_year_link(year_link: str):
    """Process a yearly link to extract and download associated documents."""
    logger.info(f"Processing year link: {year_link}")
    yearly_dir = os.path.basename(year_link.rstrip("/"))
    os.makedirs(yearly_dir, exist_ok=True)

    response = requests.get(year_link, headers=get_headers(), timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    page_id = soup.find("meta", {"name": "pageId"}).get("content")  # type: ignore
    api_url = "https://aarhus.dk/umbraco/surface/list/PaginationListItem"
    request_data = {
        "pageId": page_id,
        "dontsortbydate": "False",
        "page": 1,
        "pageSize": 1000,
        "year": "",
        "month": "",
        "tag": "",
        "lang": "da",
        "showDate": "True",
    }

    api_response = requests.get(
        api_url, params=request_data, headers=get_headers(), timeout=10
    )
    api_response.raise_for_status()
    api_soup = BeautifulSoup(api_response.text, "html.parser")

    question_links = [
        f"https://aarhus.dk/{anchor['href']}"
        for anchor in api_soup.find_all("a")
        if is_desired_url(anchor.get("href", ""))
    ]

    for question_link in question_links:
        process_question_link(yearly_dir, question_link)


def process_question_link(yearly_dir: str, question_link: str):
    """Process an individual question link to download its documents."""
    logger.info(question_link)
    question_dir = os.path.join(yearly_dir, os.path.basename(question_link.rstrip("/")))
    os.makedirs(question_dir, exist_ok=True)

    response = requests.get(question_link, headers=get_headers(), timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    documents = soup.select(".list__downloads .list__link")
    for document in documents:
        download_url = f"https://aarhus.dk{document.get('href')}"
        logger.info(f"Downloading document: {download_url}")
        download_file(question_dir, download_url)


def main():
    """Main function to scrape and process data."""
    base_url = "https://aarhus.dk/demokrati/politik/byraadet/spoergsmaal-fra-byraadets-medlemmer"
    response = requests.get(base_url, headers=get_headers(), timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    year_links = [
        f"https://aarhus.dk/{anchor['href']}"
        for anchor in soup.find_all("a", class_="link-box link-box__article")
        if is_desired_url(anchor.get("href", ""))
    ]

    for year_link in year_links:
        process_year_link(year_link)


if __name__ == "__main__":
    main()
