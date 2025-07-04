# Dataset Download Automation

This project automates the process of downloading datasets from [data.gov.in](https://www.data.gov.in/resources?title=art&sortby=created), including handling CAPTCHA challenges using the Mistral API.

## Project Structure

- **downloader.py**: Main automation script. Uses Selenium to navigate the website, fill forms, solve CAPTCHAs with the Mistral API, and download datasets.
- **.env**: Stores environment variables, including your `MISTRAL_API_KEY`.
- **mistral.txt**: Example scripts and API usage for interacting with the Mistral API via NVIDIA endpoints.
- **plan.md**: Development plan, technology stack suggestions, and step-by-step guide for building and improving the automation app.
- **requirements.txt**: Python dependencies required for running the automation.
- **screencapture-data-gov-in-resources-2025-05-09-20_02_24.png**, **Screenshot 2025-05-09 200501.png**: Reference screenshots for UI and automation context.

## Setup

1. **Install Python 3.7+**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   - Create a `.env` file with your Mistral API key:
     ```
     MISTRAL_API_KEY=your_api_key_here
     ```

## Getting a Mistral API Key

To obtain a Mistral API key, visit:

[NVIDIA Build - Mistral Medium 3 Instruct](https://build.nvidia.com/mistralai/mistral-medium-3-instruct)

Follow the instructions on the page to generate your API key.

## Usage

Run the automation script:
```bash
python downloader.py
```

The script will:
- Open the target website
- Locate and click download buttons
- Fill required form fields
- Solve CAPTCHA using the Mistral API
- Download datasets automatically

## Notes

- Refer to `plan.md` for detailed development steps and improvement ideas.
- See `mistral.txt` for sample code on using the Mistral API directly.
- Ensure Chrome browser is installed for Selenium WebDriver.
