# Add environment variables to suppress TensorFlow messages
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logging
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable GPU

# Add dotenv import and loading at the start of the file
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback
import requests
import base64
import json

# URL of the website to automate
URL = "https://www.data.gov.in/resources?title=art&sortby=created"


def setup_driver():
    """Sets up the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    # Add options to disable ML features and suppress TensorFlow messages
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-features=IsolateOrigins')
    options.add_argument('--disable-site-isolation-trials')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    # Set window size to avoid any dynamic resizing
    driver.set_window_size(1920, 1080)
    return driver

def navigate_to_page(driver, url):
    """Navigates to the specified URL."""
    driver.get(url)
    print(f"Navigated to: {url}")

def click_download_trigger_button(driver):
    """Finds and clicks the Download button/icon to trigger the form."""
    # XPath targeting the specific download icon structure from the screenshot
    xpath_candidates = [
        # Primary: CSV download button with icon and text, as shown in screenshot
        "//a[contains(@class, 'resource-node-download') and .//span[contains(@class, 'csv-icon')] and contains(., 'Download')]",
        # Secondary: Any anchor with CSV icon and Download text
        "//a[.//span[contains(@class, 'csv-icon')] and contains(., 'Download')]",
        # Tertiary: Any anchor with Download text and CSV in class
        "//a[contains(@class, 'csv') and contains(., 'Download')]",
        # Fallback: Any anchor/button with Download text
        "//a[contains(., 'Download')]",
        "//button[contains(., 'Download')]"
    ]

    for i, xpath in enumerate(xpath_candidates):
        try:
            print(f"Attempting to click Download button with XPath candidate {i+1}: {xpath}")
            download_button = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            # Scroll the button into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
            time.sleep(1) # Brief pause after scroll
            # Wait for element to be clickable after scrolling
            download_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].click();", download_button)
            print(f"Successfully clicked the Download button using XPath: {xpath}")
            time.sleep(3)  # Wait for the modal/form to appear
            return True
        except Exception as e:
            print(f"Attempt {i+1} failed for XPath '{xpath}': {e}")
            if i == len(xpath_candidates) - 1:
                 print("All XPath candidates for Download button failed.")
                 return False
    return False # Should not be reached if loop completes

def get_captcha_text(driver):
    """Captures CAPTCHA image and uses Mistral AI to recognize text."""
    try:
        # Wait for CAPTCHA image to be visible with more flexible attributes
        captcha_wait = WebDriverWait(driver, 15)
        captcha_img = captcha_wait.until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'img-fluid') and (contains(@label, 'Captcha') or contains(@aria-label, 'CAPTCHA'))]")))
        
        # Get the src URL of the CAPTCHA image
        captcha_src = captcha_img.get_attribute('src')
        if not captcha_src:
            print("CAPTCHA image src not found.")
            return None
        
        # Download the image from the src URL
        response = requests.get(captcha_src)
        if response.status_code != 200:
            print(f"Failed to download CAPTCHA image: {response.status_code}")
            return None
        
        # Convert the image to base64
        image_b64 = base64.b64encode(response.content).decode()
        
        # Mistral AI API setup
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        stream = True
        
        # Get API key from environment variable
        api_key = os.getenv('MISTRAL_API_KEY')
        if not api_key:
            print("MISTRAL_API_KEY not found in environment variables")
            print("Current environment variables:", os.environ)
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream" if stream else "application/json"
        }
        
        payload = {
            "model": 'mistralai/mistral-medium-3-instruct',
            "messages": [
                {
                    "role": "user",
                    "content": f'What is the text shown in this image, no spaces or powers allowed, just numbers and letters, all caps, should be 6 characters long <img src="data:image/png;base64,{image_b64}" />'
                }
            ],
            "max_tokens": 512,
            "temperature": 1.00,
            "top_p": 1.00,
            "stream": stream
        }
        
        # Send request to Mistral AI
        response = requests.post(invoke_url, headers=headers, json=payload)
        
        # Process streaming response
        if stream:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data: "):
                        try:
                            data = json.loads(decoded_line[6:])
                            if 'choices' in data and len(data['choices']) > 0:
                                content = data['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    full_response += content
                        except json.JSONDecodeError:
                            continue
            
            # Clean up the response text (remove any extra text or formatting)
            captcha_text = ''.join(c for c in full_response if c.isalnum())
            
            # Ensure we have exactly 6 characters
            if len(captcha_text) != 6:
                print(f"Warning: Mistral AI returned {len(captcha_text)} characters instead of 6")
                return None
            
            return captcha_text
        else:
            print("Non-streaming response not supported")
            return None
            
    except Exception as e:
        print(f"Error getting CAPTCHA text: {str(e)}")
        return None

def get_main_tab_handle(driver):
    """Returns the handle of the main tab."""
    return driver.current_window_handle

def ensure_main_tab_focus(driver, main_tab_handle):
    """Ensures the main tab is focused without closing other tabs."""
    current_handle = driver.current_window_handle
    if current_handle != main_tab_handle:
        # Switch back to main tab if we're not on it
        driver.switch_to.window(main_tab_handle)
        print("Switched focus back to main tab")

def fill_form(driver, main_tab_handle):
    """Fills the download form with only required fields and automates CAPTCHA input."""
    try:
        form_element_wait = WebDriverWait(driver, 30) # Increased wait time for form elements

        # Wait for form to be fully loaded
        time.sleep(2)

        # Select Usage Type: Non Commercial (radio) by clicking its label
        usage_label = form_element_wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(@class, 'custom-control-label') and contains(text(), 'Non Commercial')]")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", usage_label)
        time.sleep(1)
        usage_label.click()
        print("Selected Usage Type: Non Commercial via label")

        # Select Purpose: Academia (checkbox) by clicking its label
        purpose_label = form_element_wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(@class, 'custom-control-label') and contains(text(), 'Academia')]")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", purpose_label)
        time.sleep(1)
        purpose_label.click()
        print("Checked Purpose: Academia via label")

        # Wait for CAPTCHA input field to appear with more specific XPath
        print("Waiting for CAPTCHA input field to appear...")
        try:
            captcha_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//input[@id='input-3' and @name='form_captcha']]"))
            )
            print("CAPTCHA input field found.")
        except Exception as e:
            print(f"Could not find CAPTCHA input field: {str(e)}")
            # Try alternative XPath
            try:
                captcha_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='text' and contains(@placeholder, 'code')]"))
                )
                print("Found CAPTCHA input field using alternative XPath.")
            except Exception as e2:
                print(f"Could not find CAPTCHA input field with alternative XPath: {str(e2)}")
                return False

        # Try to solve CAPTCHA automatically
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"Attempting to solve CAPTCHA (attempt {attempt + 1}/{max_attempts})")
            captcha_text = get_captcha_text(driver)
            if captcha_text:
                try:
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_text)
                    print(f"Filled CAPTCHA: {captcha_text}")
                    
                    # Click Download/Submit button
                    download_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(@class, 'btn-secondary') and contains(@class, 'btn-block') and contains(., 'Download')]")
                    ))
                    
                    # Ensure CAPTCHA input field is filled with 6 characters before clicking download
                    if len(captcha_input.get_attribute('value')) == 6:
                        download_btn.click()
                        print("Download button clicked.")
                        
                        # Immediately switch back to main tab without closing others
                        time.sleep(1)  # Brief pause to allow new tab to open
                        ensure_main_tab_focus(driver, main_tab_handle)
                        
                        # Wait for download to start or modal to close
                        try:
                            WebDriverWait(driver, 30).until_not(EC.presence_of_element_located(
                                (By.XPATH, "//button[contains(@class, 'btn-secondary') and contains(@class, 'btn-block') and contains(., 'Download')]")
                            ))
                            print("Modal closed or download started.")
                            return True
                        except Exception as e_modal:
                            print(f"Modal did not close, CAPTCHA might be incorrect: {str(e_modal)}")
                            continue
                    else:
                        print("CAPTCHA input is not 6 characters long.")
                except Exception as e_input:
                    print(f"Error filling CAPTCHA input: {str(e_input)}")
                    continue
            
            print(f"CAPTCHA recognition failed on attempt {attempt + 1} of {max_attempts}")
            time.sleep(2)  # Wait before next attempt
        
        print("All CAPTCHA recognition attempts failed")
        return False
        
    except Exception as e_fill_form:
        print(f"Error in fill_form: {type(e_fill_form).__name__} - {e_fill_form}")
        print("Traceback (fill_form):")
        traceback.print_exc()
        return False

def main():
    """Main function to run the automation."""
    driver = setup_driver()
    
    # Store the main tab handle
    main_tab_handle = get_main_tab_handle(driver)
    
    # Navigate to initial URL only once
    print(f"\n--- Initial Navigation to: {URL} ---")
    navigate_to_page(driver, URL)
    page_num = 1

    while True:
        # Ensure we're on the main tab before processing
        ensure_main_tab_focus(driver, main_tab_handle)
        
        print(f"\n--- Processing Listing Page {page_num} ---")

        # Find all visible download buttons on the listing page
        download_buttons_xpath = "//a[contains(@class, 'active') and .//span[text()='Download']]"
        try:
            print(f"Attempting to find all download buttons with XPath: {download_buttons_xpath}")
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, download_buttons_xpath))
            )
            download_buttons = driver.find_elements(By.XPATH, download_buttons_xpath)
            print(f"Found {len(download_buttons)} download buttons on listing page {page_num}.")
        except Exception as e:
            print(f"Could not find download buttons on listing page {page_num}: {e}")
            break

        if not download_buttons:
            print(f"No download buttons found on page {page_num}. Ending process.")
            break

        for i, download_button in enumerate(download_buttons):
            print(f"\nProcessing dataset {i+1}/{len(download_buttons)} from page {page_num}")
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                time.sleep(1)
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, download_buttons_xpath)))
                driver.execute_script("arguments[0].click();", download_button)
                print(f"Clicked download button for dataset {i+1} on listing page {page_num}.")
                time.sleep(3)
                if not fill_form(driver, main_tab_handle):  # Pass main_tab_handle to fill_form
                    print("Form submission failed, skipping to next dataset.")
                    continue
                print(f"Form processing attempted for dataset {i+1} on listing page {page_num}.")
                time.sleep(7)
            except Exception as e_detail:
                print(f"An error occurred while processing download button {i+1}: {e_detail}")
                print("Attempting to continue with the next dataset on the current listing page.")

        # After processing all download buttons, try to go to the next listing page.
        print(f"\n--- Finished datasets for listing page {page_num}. Checking for next page. ---")
        
        try:
            # First check if there's a disabled next button (indicating end of pages)
            disabled_next_xpath = "//li[contains(@class, 'page-item') and contains(@class, 'disabled')]//span[contains(@aria-label, 'Go to next page')]"
            disabled_next = driver.find_elements(By.XPATH, disabled_next_xpath)
            
            if disabled_next:
                print("Found disabled next button. This is the last page.")
                break
            
            # If no disabled button, look for active next button
            next_page_button_xpath = "//button[contains(@aria-label, 'Go to next page') and not(contains(@aria-disabled, 'true'))]"
            print(f"Looking for active 'Next' page button with XPath: {next_page_button_xpath}")
            
            next_page_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, next_page_button_xpath))
            )
            
            # Click the next button and wait for content to update
            driver.execute_script("arguments[0].click();", next_page_button)
            print("Clicked next page button.")
            
            # Wait for the page content to update
            time.sleep(3)
            page_num += 1
            
        except Exception as e:
            print(f"Could not find or click next page button: {e}")
            break

    print("\n========================================================================")
    print("Automation script has finished its run.")
    print("Please check your download directory and console logs for details.")
    print("The browser will remain open for 30 seconds for final observation.")
    print("========================================================================")
    time.sleep(30)
    driver.quit()
    print("Browser closed.")

if __name__ == "__main__":
    main()