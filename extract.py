import os
import re
import subprocess
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def setup_driver():
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)


def extract_date(text):
    match = re.search(r"(\d{4})\.(\d{2})\.\d{2}", text)
    if match:
        year, month = match.groups()
        return year, month
    return None, None


def get_download_link(edition_id):
    return f"https://www.wbc.poznan.pl/Content/{edition_id}/download/"


def download_with_wget(url, filepath):
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

        return process.returncode == 0

    except Exception:
        return False


def scrape_and_download(url, target_year=None, target_month=None):
    base_dir = "downloads"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    driver = setup_driver()
    try:
        print("Loading page...")
        driver.get(url)

        wait = WebDriverWait(driver, 10)
        wait.until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "tab-content__tree-fake-list-item")
            )
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")

        items = soup.find_all("div", class_="tab-content__tree-fake-list-item")
        print(f"Found {len(items)} items")

        downloads = []
        for item in items:
            content_link = item.find("a", {"aria-label": "Show content"})
            if not content_link:
                continue

            href = content_link["href"]
            edition_id_match = re.search(r"edition/(\d+)", href)
            if not edition_id_match:
                continue

            edition_id = edition_id_match.group(1)

            title_link = item.find("a", class_="tab-content__tree-link")
            if not title_link:
                continue

            title = title_link.text.strip()
            year, month = extract_date(title)

            if year and (target_year is None or year == target_year):
                if target_month is None or month == target_month:
                    downloads.append(
                        {
                            "title": title,
                            "year": year,
                            "month": month,
                            "edition_id": edition_id,
                        }
                    )

        total_downloads = len(downloads)
        print(f"\nPreparing to download {total_downloads} files")

        for i, item in enumerate(downloads, 1):
            year_dir = os.path.join(base_dir, item["year"])
            month_dir = os.path.join(year_dir, item["month"])
            if not os.path.exists(month_dir):
                os.makedirs(month_dir)

            safe_filename = re.sub(r'[<>:"/\\|?*]', "_", item["title"]) + ".pdf"
            filepath = os.path.join(month_dir, safe_filename)

            if os.path.exists(filepath):
                print(f"[{i}/{total_downloads}] File exists, skipping: {item['title']}")
                continue

            download_url = get_download_link(item["edition_id"])
            print(f"\n[{i}/{total_downloads}] Downloading: {item['title']}")

            success = download_with_wget(download_url, filepath)

            if success:
                print(f"\u2713 Successfully downloaded: {item['title']}")
            else:
                print(f"\u2717 Failed to download: {item['title']}")

            time.sleep(1)

    finally:
        driver.quit()


if __name__ == "__main__":
    print("WBC Poznan Digital Library Scraper")
    print("-" * 50)

    base_url = input("Enter the base URL of the webpage: ")
    year_input = input("Enter a specific year to download : ").strip()
    month_input = input(
        "Enter a specific month (MM) to download(press enter for all months) : "
    ).strip()

    target_year = year_input if year_input else None
    target_month = month_input if month_input else None

    print("\nStarting scraping process...")
    scrape_and_download(base_url, target_year, target_month)
