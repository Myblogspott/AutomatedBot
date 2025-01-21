from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os
from openai import ChatCompletion
import openai

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        log_environment()
        print("ChromeDriver and Browser are compatible.")
        return driver
    except Exception as e:
        print("Error initializing ChromeDriver. Ensure compatibility:", e)
        raise

def log_environment():
    from selenium import __version__ as selenium_version
    import platform
    try:
        print("Environment Debug Info:")
        print(f"Selenium Version: {selenium_version}")
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"ChromeDriver Version: {ChromeDriverManager().driver().version}")
    except Exception as e:
        print("Error logging environment details: ", e)

def analyze_job_description(job_description):
    prompt = f"Match the following job description to a resume. Highlight key skills and experiences that fit:\n\n{job_description}"
    completion = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message['content']

def fill_dynamic_form(question_text):
    prompt = f"Answer this question for a job application based on the question context: {question_text}"
    completion = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message['content']

def decide_to_apply(job_description):
    prompt = f"Should I apply for this job? Analyze based on relevance to AI/ML skills:\n\n{job_description}"
    completion = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    decision = completion.choices[0].message['content']
    return "yes" in decision.lower()

def handle_error_with_ai(error_message, dom_snapshot=None):
    """
    Send error details to the AI model and return its suggestions.
    """
    # Truncate DOM snapshot to avoid exceeding token limits
    if dom_snapshot:
        dom_snapshot = dom_snapshot[:1000]  # Limit to 1000 characters

    prompt = f"""
    Analyze the following Selenium error and suggest a solution:
    Error: {error_message}
    DOM Snapshot:
    {dom_snapshot or 'No snapshot available'}
    """
    try:
        completion = ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message['content']
    except Exception as e:
        print("Failed to get AI suggestions: ", e)
        return "retry"  # Default to a retry suggestion

def apply_ai_suggestion(ai_suggestion):
    """
    Parse and implement AI suggestions dynamically.
    """
    if not ai_suggestion:
        print("No AI suggestion received.")
        return False

    print("AI Suggestion: ", ai_suggestion)
    # Implement a simple action parser here for common fixes
    if "retry" in ai_suggestion.lower():
        print("Retrying the last action...")
        return True
    if "update chromedriver" in ai_suggestion.lower() or "browser compatibility" in ai_suggestion.lower():
        print("Suggestion to update ChromeDriver or check browser compatibility. Manual intervention required.")
        return False  # Needs manual intervention
    else:
        print("No actionable suggestion found.")
        return False

# Initialize driver and wait objects
driver = setup_driver()
wait = WebDriverWait(driver, 15)

# Step 3: Navigate and Filter Search
def navigate_and_filter():
    driver.get("https://www.linkedin.com/jobs/")
    input("Please log in to LinkedIn and press Enter once you're ready.")

    try:
        # Wait for the search box to be interactable
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'search-global-typeahead__input')]")))
        search_box.send_keys("AI/ML Engineer")
        search_box.send_keys(Keys.RETURN)
    except Exception as e:
        print("Error locating the search box: ", e)
        time.sleep(10)
        return

    # Wait for filters to load and ensure visibility
    for _ in range(3):  # Retry up to 3 times
        try:
            filters_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Experience level filter. Clicking this button displays all Experience level filter options.']")))
            filters_button.click()
            break
        except Exception as e:
            print("Retry loading filters due to error: ", e)
            time.sleep(5)
    else:
        print("Failed to load filters after retries.")
        return

    # Apply filters for 'Easy Apply' and 'Entry Level'
    try:
        easy_apply_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Easy Apply filter.']")))
        if easy_apply_button.is_displayed():
            easy_apply_button.click()

        entry_level_label = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//label[@for='experience-2']")))
        if entry_level_label.is_displayed():
            entry_level_label.click()

        # Check if results are available
        try:
            results_count = driver.find_element(By.XPATH, "//span[contains(@class, 'results-context-header')]").text
            print(f"Results found: {results_count}")
        except:
            print("No results found. Exiting.")
            return

    except Exception as e:
        print("Error applying filters: ", e)
        time.sleep(10)

# Step 4: Automated Application Process
def apply_to_jobs():
    job_links = set()
    while True:
        job_cards = driver.find_elements(By.XPATH, "//a[@data-control-name='job_card']")
        for card in job_cards:
            job_link = card.get_attribute("href")
            if job_link not in job_links:
                job_links.add(job_link)

        for link in job_links:
            driver.get(link)
            try:
                job_description = driver.find_element(By.XPATH, "//section[contains(@class, 'description')]").text
                if not decide_to_apply(job_description):
                    print(f"Skipping job: {link}")
                    continue

                easy_apply_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Easy Apply')]")))
                easy_apply_button.click()

                form_fields = driver.find_elements(By.XPATH, "//input | //textarea")
                for field in form_fields:
                    question_text = field.get_attribute("aria-label") or field.get_attribute("placeholder")
                    if question_text:
                        field.send_keys(fill_dynamic_form(question_text))

                while True:
                    try:
                        next_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Next') or contains(text(),'Submit')]")))
                        next_button.click()
                        time.sleep(1)

                        if "Submit" in next_button.text:
                            print(f"Applied to {link}. Moving to next job.")
                            break
                    except Exception as e:
                        print("Error navigating form: ", e)
                        suggestion = handle_error_with_ai(str(e), driver.page_source)
                        if not apply_ai_suggestion(suggestion):
                            break

                print(f"Applied to {link}")
            except Exception as e:
                print(f"Skipped {link} due to error: {e}")
                suggestion = handle_error_with_ai(str(e), driver.page_source)
                if not apply_ai_suggestion(suggestion):
                    continue

        try:
            next_page_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label,'Next')]")))
            next_page_button.click()
            time.sleep(2)
        except Exception as e:
            print("No more pages or jobs found: ", e)
            suggestion = handle_error_with_ai(str(e), driver.page_source)
            if not apply_ai_suggestion(suggestion):
                break

# Step 5: Stop Condition
if __name__ == "__main__":
    try:
        navigate_and_filter()
        apply_to_jobs()
    finally:
        driver.quit()
