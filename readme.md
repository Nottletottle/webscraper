# WBC Poznan Digital Library Scraper

This script allows you to scrape and download PDF files from the WBC Poznan Digital Library. It automates the process of browsing the library, finding specific editions, and downloading them based on the year and month criteria provided by the user.

## Features

- Extracts content metadata from the WBC Poznan Digital Library.
- Allows filtering downloads by year and month.
- Automatically organizes downloaded files into year/month subdirectories.
- Uses Selenium for web automation and `wget` for reliable downloading.

## Requirements

- Python 3.8 or higher
- Google Chrome browser
- ChromeDriver installed and available in your system PATH
- `wget` installed on your system

## Installation Guide

1. Clone the repository or download the script.
2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows, use `.venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. Ensure you have Google Chrome and ChromeDriver installed. You can download ChromeDriver from the [official site](https://sites.google.com/chromium.org/driver/).
4. Ensure `wget` is installed on your system. You can install it using your package manager:

   - For Debian/Ubuntu:
     ```bash
     sudo apt install wget
     ```
   - For macOS (with Homebrew):
     ```bash
     brew install wget
     ```

## Usage

1. Run the script:

   ```bash
   python extract.py
   ```

2. Provide the following inputs when prompted:
   - **Base URL**: The URL of the webpage you want to scrape (e.g., `https://www.wbc.poznan.pl/dlibra/publication/<some-id>#structure`).
   - **Year**: Specify the year for which you want to download files (e.g., `1945`).
   - **Month**: Specify the month in `MM` format (e.g., `01` for January). Leave blank to download all months.

3. The script will:
   - Scrape the webpage for available editions.
   - Filter editions based on the specified year and month.
   - Download the matching editions as PDFs into a `downloads` folder, organized by year and month.

## Directory Structure

The script creates a `downloads` directory with the following structure:

```
downloads/
  ├──1945/
  │   ├──01/
  │   ├──02/
  │   └──12/
  ├──1946/
      └──01/
```

Each PDF file is saved with a sanitized filename based on its title.

## Requirements File

To install the requirements, run:

```bash
pip install -r requirements.txt
```

## Notes

- Ensure ChromeDriver version matches your installed Chrome version.
- The script uses Selenium in headless mode to avoid opening a browser window during execution.
- If you encounter issues with `wget`, ensure it is installed and accessible from your system PATH.
- Adjust the `WebDriverWait` timeout if the page takes longer to load on your network.

## Troubleshooting

- **ChromeDriver Not Found**: Make sure ChromeDriver is installed and added to your PATH.
- **Timeout Errors**: Increase the timeout in the `WebDriverWait` call in the script.
- **Invalid Downloads**: Check if the download URL format has changed on the website.

## Disclaimer

This script is provided for educational purposes only. Ensure you comply with the terms of service of the WBC Poznan Digital Library before using this script.

