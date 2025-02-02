import logging
import os
import platform
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper_debug.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def log_system_info():
    """Log system and environment information"""
    logging.info("System Information:")
    logging.info(f"Python Version: {sys.version}")
    logging.info(f"Platform: {platform.platform()}")
    logging.info(f"Chrome Driver Path: {webdriver.chrome.service.Service().path}")
    try:
        chrome_version = (
            subprocess.check_output(["google-chrome", "--version"]).decode().strip()
        )
        logging.info(f"Chrome Version: {chrome_version}")
    except:
        logging.warning("Could not determine Chrome version")


def setup_driver():
    from selenium.webdriver.chrome.options import Options

    logging.info("Setting up Chrome driver")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=en-US")  # Force English locale

    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Chrome driver setup successful")
        return driver
    except WebDriverException as e:
        logging.error(f"Failed to setup Chrome driver: {str(e)}")
        raise


def extract_date(text):
    logging.debug(f"Attempting to extract date from: {text}")

    match = re.search(r"(\d{4})(?:\.(\d{2})\.\d{2})?", text)
    if match:
        year, month = match.group(1), match.group(2)
        logging.debug(f"Extracted - Year: {year}, Month: {month or 'None'}")
        return year, month
    logging.warning(f"Could not extract date from text: {text}")
    return None, None


def get_base_domain(url):
    try:
        parsed = urlparse(url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        return base_domain.rstrip("/")
    except Exception as e:
        logging.error(f"Error parsing URL {url}: {str(e)}")
        return None


def get_download_link(edition_id, url):
    base_domain = get_base_domain(url)
    if not base_domain:
        logging.error(f"Could not extract base domain from URL: {url}")
        return None

    download_url = f"{base_domain}/Content/{edition_id}/download/"
    logging.debug(f"Generated download link: {download_url}")
    return download_url


def get_file_extension(url):
    """
    Determine the file extension from Content-Disposition header
    Falls back to .pdf if unable to determine
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_disposition = response.headers.get("Content-Disposition", "")

        if "filename" in content_disposition:
            filename_match = re.search(
                r'filename=(?:"([^"]+)"|([^;]+))', content_disposition
            )
            if filename_match:
                filename = filename_match.group(1) or filename_match.group(2)
                ext = os.path.splitext(filename)[1]
                if ext:
                    logging.debug(
                        f"Extension determined from Content-Disposition: {ext}"
                    )
                    return ext

        logging.warning(
            f"Could not determine file extension from Content-Disposition, defaulting to .pdf"
        )
        return ".pdf"

    except Exception as e:
        logging.error(f"Error determining file extension: {str(e)}")
        return ".pdf"


def download_with_wget(url, filepath):
    logging.info(f"Attempting to download: {url}")
    try:
        command = [
            "wget",
            "--progress=bar:force",
            "--tries=3",
            "--timeout=30",
            "-O",
            filepath,
            url,
        ]

        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        if process.returncode == 0:
            logging.info(f"Download successful: {filepath}")
            return True
        else:
            logging.error(f"Download failed with return code {process.returncode}")
            logging.error(f"stderr: {process.stderr}")
            return False

    except Exception as e:
        logging.error(f"Download failed with exception: {str(e)}")
        return False


def get_save_directory(base_dir, year, month):
    """
    Determine the appropriate directory to save the file based on date information
    """
    if year and month:
        return os.path.join(base_dir, year, month)
    elif year:
        return os.path.join(base_dir, year, "unknown_month")
    else:
        return os.path.join(base_dir, "unknown_date")


def scrape_and_download(url, target_year=None, target_month=None):
    logging.info(f"Starting scrape_and_download with URL: {url}")
    logging.info(f"Target year: {target_year}, Target month: {target_month}")

    base_dir = "downloads"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        logging.info(f"Created base directory: {base_dir}")

    driver = setup_driver()
    try:
        logging.info("Loading page...")
        driver.get(url)
        logging.debug(f"Current URL: {driver.current_url}")

        wait_time = 30
        logging.info(f"Waiting up to {wait_time} seconds for elements to load...")

        try:
            wait = WebDriverWait(driver, wait_time)
            wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "tab-content__tree-fake-list-item")
                )
            )
            time.sleep(5)
            logging.info("Initial elements found, waiting for page to stabilize.....")
        except TimeoutException as e:
            logging.error(f"Timeout waiting for elements: {str(e)}")
            logging.debug(f"Page source at timeout: {driver.page_source[:1000]}...")
            raise

        page_source = driver.page_source
        logging.debug(f"Page source length: {len(page_source)}")

        soup = BeautifulSoup(page_source, "html.parser")
        items = soup.find_all(
            ["div", "span"], class_="tab-content__tree-fake-list-item"
        )
        logging.info(f"Found {len(items)} items")

        downloads = []
        for idx, item in enumerate(items, 1):
            logging.debug(f"Processing item {idx}/{len(items)}")

            content_link = item.find("a", {"aria-label": "Pokaż treść"})
            if not content_link:
                logging.warning(f"No content link found in item {idx}")
                continue

            href = content_link["href"]
            logging.debug(f"Found href: {href}")

            edition_id_match = re.search(r"edition/(\d+)", href)
            if not edition_id_match:
                logging.warning(f"No edition ID found in href: {href}")
                continue

            edition_id = edition_id_match.group(1)
            logging.debug(f"Extracted edition ID: {edition_id}")

            title_link = item.find("a", class_="tab-content__tree-link")
            if not title_link:
                logging.warning(f"No title link found for edition ID: {edition_id}")
                continue

            title = title_link.text.strip()
            year, month = extract_date(title)

            logging.debug(f"Item {idx}: Title: {title}, Year: {year}, Month: {month}")

            # Modified logic to include items without dates if no target is specified
            should_download = False
            if target_year is None and target_month is None:
                should_download = True
            elif year is None:
                should_download = (
                    False  # Skip undated items if targeting specific dates
                )
            elif target_year and year == target_year:
                if target_month is None or month == target_month:
                    should_download = True

            if should_download:
                downloads.append(
                    {
                        "title": title,
                        "year": year,
                        "month": month,
                        "edition_id": edition_id,
                    }
                )
                logging.info(f"Added item to downloads: {title}")
            else:
                logging.debug(f"Skipped item: {title}")

        total_downloads = len(downloads)
        logging.info(f"Prepared {total_downloads} files for download")

        if total_downloads == 0:
            logging.warning("No files matched the criteria for download")
            return []

        for i, item in enumerate(downloads, 1):
            # Get appropriate directory
            save_dir = get_save_directory(base_dir, item["year"], item["month"])
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                logging.info(f"Created directory: {save_dir}")

            download_url = get_download_link(item["edition_id"], url)
            file_extension = get_file_extension(download_url)
            safe_filename = re.sub(r'[<>:"/\\|?*]', "_", item["title"]) + file_extension
            filepath = os.path.join(save_dir, safe_filename)

            if os.path.exists(filepath):
                logging.info(
                    f"[{i}/{total_downloads}] File exists, skipping: {item['title']}"
                )
                continue

            logging.info(f"\n[{i}/{total_downloads}] Downloading: {item['title']}")
            logging.debug(f"Download URL: {download_url}")
            logging.debug(f"Save path: {filepath}")

            success = download_with_wget(download_url, filepath)

            if success:
                logging.info(f"\u2713 Successfully downloaded: {item['title']}")
            else:
                logging.error(f"\u2717 Failed to download: {item['title']}")

            time.sleep(1)

        return downloads

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise
    finally:
        driver.quit()
        logging.info("Driver closed")


if __name__ == "__main__":
    try:
        print("WBC Poznan Digital Library Scraper")
        print("-" * 50)

        log_system_info()

        base_url = input("Enter the base URL of the webpage: ")
        year_input = input(
            "Enter a specific year to download (press enter for all years): "
        ).strip()
        month_input = input(
            "Enter a specific month (MM) to download (press enter for all months): "
        ).strip()

        target_year = year_input if year_input else None
        target_month = month_input if month_input else None

        logging.info("Starting scraping process...")
        downloads = scrape_and_download(base_url, target_year, target_month)

        if not downloads:
            logging.error("No files were found matching the specified criteria")
            sys.exit(1)

    except Exception as e:
        logging.error(f"Script failed with error {e}", exc_info=True)
        sys.exit(1)
