import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
import time
import os
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitLabMRDocumentationGenerator:
    def __init__(self, gitlab_url: str, private_token: str):
        """
        Initialize the documentation generator

        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.example.com)
            private_token: GitLab private access token
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        # Initialize session tracking
        self.api_access_working = False
        self.browser_session_available = False

        # Setup Chrome driver
        self.setup_chrome_driver()

        # Verify GitLab authentication
        self.verify_gitlab_authentication()

        # Initialize Gemini web interface
        self.setup_gemini_web_interface()

    def verify_gitlab_authentication(self):
        """Verify GitLab authentication and check if browser login is needed"""
        try:
            # Test API access first
            url = f"{self.gitlab_url}/api/v4/user"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"GitLab API access verified for user: {user_info.get('name', 'Unknown')}")
                self.api_access_working = True

                # Since API is working, check browser session more gently
                logger.info("API access confirmed. Checking browser session...")
                self.check_browser_session_gentle()

            else:
                logger.warning(f"GitLab API access failed: {response.status_code}")
                logger.info("API access might be limited, will rely on browser session")
                self.api_access_working = False

                # If API fails, browser session becomes critical
                self.check_browser_session_strict()

        except Exception as e:
            logger.error(f"Error verifying GitLab authentication: {e}")
            self.api_access_working = False
            self.check_browser_session_strict()

    def check_browser_session_gentle(self):
        """Gently check browser session when API is working"""
        try:
            logger.info("Performing gentle browser session check...")
            self.driver.get(self.gitlab_url)
            time.sleep(2)  # Shorter wait since API is working

            # Look for login indicators
            login_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                         "input[type='password'], .login-form, #user_login, #user_password, .sign-in-box")

            if login_indicators:
                logger.info("Browser session requires sign-in, but API access is working.")
                logger.info("Browser sign-in will be needed for viewing MR pages.")

                # Ask user if they want to sign in now or skip browser features
                response = input(
                    "Do you want to sign in to GitLab in browser now? This enables viewing MR pages. (y/n): ").lower().strip()
                if response == 'y':
                    self.prompt_gitlab_signin()
                else:
                    logger.info("Skipping browser sign-in. Will rely on API access only.")
                    self.browser_session_available = False
            else:
                logger.info("Browser session appears to be active")
                self.browser_session_available = True

        except Exception as e:
            logger.warning(f"Error checking browser session gently: {e}")
            self.browser_session_available = False

    def check_browser_session_strict(self):
        """Strictly check browser session when API is not working"""
        try:
            logger.info("API access unavailable. Browser session is required.")
            self.driver.get(self.gitlab_url)
            time.sleep(3)

            # Look for login indicators
            login_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                         "input[type='password'], .login-form, #user_login, #user_password, .sign-in-box")

            if login_indicators:
                logger.warning("GitLab browser session not found. Please sign in.")
                self.prompt_gitlab_signin()
            else:
                # Look for dashboard indicators
                dashboard_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                                 ".dashboard, .nav-sidebar, .header-logo, .user-menu, .project-item-select")

                if dashboard_indicators:
                    logger.info("GitLab browser session verified")
                    self.browser_session_available = True
                else:
                    logger.warning("GitLab page loaded but unclear if signed in")
                    self.prompt_gitlab_signin()

        except Exception as e:
            logger.error(f"Error checking GitLab session: {e}")
            self.prompt_gitlab_signin()
        """Prompt user to sign in to GitLab"""
        logger.info("GitLab sign-in required.")
        logger.info(f"Browser is open at: {self.gitlab_url}")
        logger.info("Please sign in to GitLab manually in the browser window.")

        input("Press Enter after signing in to GitLab...")

        # Verify sign-in was successful
        try:
            self.driver.refresh()
            time.sleep(3)

            login_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                         "input[type='password'], .login-form, #user_login, #user_password, .sign-in-box")

            if login_indicators:
                logger.error("GitLab sign-in verification failed. Still on login page.")
                retry = input("Do you want to try again? (y/n): ").lower().strip()
                if retry == 'y':
                    self.prompt_gitlab_signin()
                else:
                    raise Exception("GitLab authentication required but not completed")
            else:
                logger.info("GitLab sign-in verified successfully")

        except Exception as e:
            logger.error(f"Error verifying GitLab sign-in: {e}")
            raise

    def check_mr_accessibility(self, project_id: str, mr_iid: str) -> Dict:
        """
        Check if merge request is accessible via both API and browser

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID

        Returns:
            Dictionary containing accessibility status and MR info
        """
        result = {
            'accessible': False,
            'api_accessible': False,
            'browser_accessible': False,
            'mr_info': None,
            'error': None
        }

        try:
            # First try API access if available
            if self.api_access_working:
                logger.info(f"Checking API access for MR {project_id}/{mr_iid}")
                mr_info = self.get_merge_request_info(project_id, mr_iid)

                if mr_info:
                    result['api_accessible'] = True
                    result['mr_info'] = mr_info
                    logger.info(
                        f"✓ API access successful for MR {project_id}/{mr_iid}: {mr_info.get('title', 'No title')}")
                else:
                    logger.warning(f"✗ API access failed for MR {project_id}/{mr_iid}")
            else:
                logger.info(f"Skipping API check for MR {project_id}/{mr_iid} - API not available")

            # Check browser access if browser session is available or if API failed
            if self.browser_session_available or not result['api_accessible']:
                logger.info(f"Checking browser access for MR {project_id}/{mr_iid}")
                mr_url = f"{self.gitlab_url}/{project_id}/-/merge_requests/{mr_iid}"
                self.driver.get(mr_url)
                time.sleep(3)

                # Check for access denied or not found indicators
                access_denied_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                                     ".access-denied, .not-found, .error-message, .permission-denied")

                error_messages = self.driver.find_elements(By.XPATH,
                                                           "//*[contains(text(), '404') or contains(text(), 'not found') or contains(text(), 'access denied') or contains(text(), 'permission')]")

                if access_denied_indicators or error_messages:
                    result['error'] = "Access denied or MR not found via browser"
                    logger.warning(f"✗ Browser access denied for MR {project_id}/{mr_iid}")
                else:
                    # Look for MR content indicators
                    mr_content_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                                      ".merge-request, .mr-widget, .mr-state-widget, .issuable-meta, .merge-request-details")

                    if mr_content_indicators:
                        result['browser_accessible'] = True
                        logger.info(f"✓ Browser access successful for MR {project_id}/{mr_iid}")

                        # If we don't have MR info from API, try to get basic info from browser
                        if not result['mr_info']:
                            try:
                                title_element = self.driver.find_element(By.CSS_SELECTOR,
                                                                         ".issue-title, .merge-request-title, h1, .title")
                                title = title_element.text.strip()

                                result['mr_info'] = {
                                    'title': title,
                                    'web_url': mr_url,
                                    'iid': mr_iid
                                }
                                logger.info(f"Extracted MR title from browser: {title}")
                            except:
                                logger.warning("Could not extract MR title from browser")
                    else:
                        result['error'] = "MR content not found in browser"
                        logger.warning(f"✗ MR content not accessible via browser for {project_id}/{mr_iid}")

            # Set overall accessibility
            result['accessible'] = result['api_accessible'] or result['browser_accessible']

            if result['accessible']:
                logger.info(f"✓ MR {project_id}/{mr_iid} is accessible")
            else:
                logger.error(f"✗ MR {project_id}/{mr_iid} is not accessible via any method")

        except Exception as e:
            result['error'] = f"Error checking MR accessibility: {str(e)}"
            logger.error(f"Error checking accessibility for MR {project_id}/{mr_iid}: {e}")

        return result

    def setup_chrome_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        # Remove headless mode to see Gemini interface
        # chrome_options.add_argument('--headless')  # Comment out for debugging
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-data-dir=/tmp/chrome_profile')  # Persistent session

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.maximize_window()

    def setup_gemini_web_interface(self):
        """Setup Gemini web interface"""
        try:
            logger.info("Opening Gemini web interface...")
            self.driver.get("https://gemini.google.com/")

            # Wait for page to load
            time.sleep(5)

            # Check if we need to sign in (you might need to manually sign in first time)
            try:
                # Look for the text input area
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.find_element(By.CSS_SELECTOR, "[data-test-id='input-area']") or
                                   driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true']") or
                                   driver.find_element(By.TAG_NAME, "textarea")
                )
                logger.info("Gemini interface is ready")

            except Exception as e:
                logger.warning("Gemini interface might require manual sign-in. Please sign in manually and run again.")
                logger.warning("The browser window will stay open for manual sign-in.")
                input("Press Enter after signing in to Gemini...")

        except Exception as e:
            logger.error(f"Error setting up Gemini interface: {e}")
            raise

    def get_merge_request_info(self, project_id: str, mr_iid: str) -> Dict:
        """
        Get merge request information from GitLab API

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID

        Returns:
            Dictionary containing MR information
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get MR info: {response.status_code}")
            return None

    def get_merge_request_changes(self, project_id: str, mr_iid: str) -> Dict:
        """
        Get merge request changes from GitLab API

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID

        Returns:
            Dictionary containing MR changes
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get MR changes: {response.status_code}")
            return None

    def extract_java_changes(self, changes_data: Dict) -> List[Dict]:
        """
        Extract Java file changes from the changes data

        Args:
            changes_data: MR changes data from GitLab API

        Returns:
            List of Java file changes
        """
        java_changes = []

        if 'changes' in changes_data:
            for change in changes_data['changes']:
                if change['new_path'].endswith('.java'):
                    java_changes.append({
                        'file_path': change['new_path'],
                        'old_path': change.get('old_path', change['new_path']),
                        'diff': change['diff'],
                        'new_file': change['new_file'],
                        'deleted_file': change['deleted_file'],
                        'renamed_file': change['renamed_file']
                    })

        return java_changes

    def get_file_content_via_chrome(self, project_id: str, file_path: str, ref: str = 'main') -> str:
        """
        Get file content using Chrome WebDriver (for cases where API access is restricted)

        Args:
            project_id: GitLab project ID
            file_path: Path to the file
            ref: Git reference (branch, tag, commit)

        Returns:
            File content as string
        """
        try:
            url = f"{self.gitlab_url}/{project_id}/-/raw/{ref}/{file_path}"
            self.driver.get(url)

            # Wait for content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )

            # Get the file content
            content_element = self.driver.find_element(By.TAG_NAME, "pre")
            return content_element.text

        except Exception as e:
            logger.error(f"Error getting file content via Chrome: {e}")
            return ""

    def send_prompt_to_gemini_web(self, prompt: str) -> str:
        """
        Send prompt to Gemini web interface and get response

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Gemini's response as string
        """
        try:
            logger.info("Sending prompt to Gemini...")

            # Navigate to Gemini if not already there
            if "gemini.google.com" not in self.driver.current_url:
                self.driver.get("https://gemini.google.com/")
                time.sleep(3)

            # Find the input area (try multiple selectors as Gemini's UI might change)
            input_selectors = [
                "[data-test-id='input-area']",
                "div[contenteditable='true']",
                "textarea",
                ".ql-editor",
                "[role='textbox']",
                "div[aria-label*='Message']",
                "div[placeholder*='Enter a prompt']"
            ]

            input_element = None
            for selector in input_selectors:
                try:
                    input_element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue

            if not input_element:
                # Try to find any editable element
                input_element = self.driver.find_element(By.CSS_SELECTOR, "*[contenteditable='true']")

            if not input_element:
                raise Exception("Could not find Gemini input area")

            # Clear any existing content
            input_element.click()
            time.sleep(1)

            # Select all and delete
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.5)
            input_element.send_keys(Keys.DELETE)
            time.sleep(1)

            # Type the prompt (split into chunks to avoid issues with long text)
            chunk_size = 1000
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i + chunk_size]
                input_element.send_keys(chunk)
                time.sleep(0.5)

            # Submit the prompt
            time.sleep(2)

            # Try different ways to submit
            try:
                # Method 1: Press Enter
                input_element.send_keys(Keys.ENTER)
            except:
                try:
                    # Method 2: Look for send button
                    send_button = self.driver.find_element(By.CSS_SELECTOR,
                                                           "[data-test-id='send-button'], button[aria-label*='Send'], button[title*='Send']")
                    send_button.click()
                except:
                    # Method 3: Use Ctrl+Enter
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(
                        Keys.CONTROL).perform()

            logger.info("Prompt submitted, waiting for response...")

            # Wait for response to appear
            time.sleep(5)

            # Wait for response to complete (look for indicators that generation is done)
            max_wait_time = 180  # 3 minutes max
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                try:
                    # Check if there are any loading indicators
                    loading_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                                   ".loading, .generating, [data-test-id='loading'], .spinner, .animate-spin")

                    if not loading_indicators:
                        # Check if we can find response content
                        response_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                                      "[data-test-id='response'], .response-content, .message-content")

                        if response_elements:
                            break

                    time.sleep(3)
                except:
                    time.sleep(3)

            # Extract the response
            response_text = self.extract_gemini_response()

            if not response_text:
                logger.warning("No response text found, trying alternative extraction methods")
                response_text = self.extract_gemini_response_alternative()

            return response_text

        except Exception as e:
            logger.error(f"Error sending prompt to Gemini: {e}")
            return f"Error getting response from Gemini: {str(e)}"

    def extract_gemini_response(self) -> str:
        """Extract response from Gemini web interface"""
        try:
            # Try multiple selectors to find the response
            response_selectors = [
                "[data-test-id='response']",
                ".response-content",
                ".message-content",
                ".model-response",
                "div[role='presentation'] div[data-test-id]",
                ".conversation-turn:last-child",
                "[data-testid='conversation-turn-3']",
                ".response-container"
            ]

            for selector in response_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Get the last element (most recent response)
                        response_element = elements[-1]
                        response_text = response_element.text.strip()
                        if response_text and len(response_text) > 50:  # Ensure it's substantial
                            return response_text
                except:
                    continue

            return ""

        except Exception as e:
            logger.error(f"Error extracting Gemini response: {e}")
            return ""

    def extract_gemini_response_alternative(self) -> str:
        """Alternative method to extract Gemini response"""
        try:
            # Get all text from the page and try to identify the response
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Look for patterns that might indicate the start of a response
            # This is a fallback method and might need adjustment based on actual UI
            lines = page_text.split('\n')
            response_lines = []
            found_response = False

            for line in lines:
                if any(keyword in line.lower() for keyword in ['summary', 'technical changes', 'impact analysis']):
                    found_response = True

                if found_response:
                    response_lines.append(line)

            return '\n'.join(response_lines) if response_lines else page_text[-2000:]  # Last 2000 chars as fallback

        except Exception as e:
            logger.error(f"Error in alternative response extraction: {e}")
            return "Could not extract response from Gemini"

    def analyze_code_changes_with_gemini(self, java_changes: List[Dict], mr_info: Dict) -> str:
        """
        Analyze Java code changes using Gemini web interface

        Args:
            java_changes: List of Java file changes
            mr_info: Merge request information

        Returns:
            Generated documentation string
        """
        # Prepare the prompt for Gemini
        prompt = f"""Please analyze the following GitLab merge request and generate comprehensive documentation.

**Merge Request Information:**
- Title: {mr_info.get('title', 'N/A')}
- Description: {mr_info.get('description', 'N/A')}
- Author: {mr_info.get('author', {}).get('name', 'N/A')}
- Source Branch: {mr_info.get('source_branch', 'N/A')}
- Target Branch: {mr_info.get('target_branch', 'N/A')}
- Created: {mr_info.get('created_at', 'N/A')}

**Java Code Changes:**"""

        # Add changes but limit the size to avoid overly long prompts
        for i, change in enumerate(java_changes[:5], 1):  # Limit to 5 files to avoid huge prompts
            prompt += f"""

**File {i}: {change['file_path']}**
- Status: {"New file" if change['new_file'] else "Modified file" if not change['deleted_file'] else "Deleted file"}
- Renamed: {change['renamed_file']}

**Diff (first 2000 characters):**
```diff
{change['diff'][:2000]}{'...' if len(change['diff']) > 2000 else ''}
```"""

        if len(java_changes) > 5:
            prompt += f"\n\n**Note:** {len(java_changes) - 5} additional Java files were modified but not shown here due to length constraints."

        prompt += """

Please provide documentation that includes:
1. **Summary**: Brief overview of what this merge request accomplishes
2. **Technical Changes**: Detailed explanation of code modifications, new features, or bug fixes
3. **Impact Analysis**: What systems/components are affected
4. **Breaking Changes**: Any breaking changes (if applicable)
5. **Testing Considerations**: What should be tested
6. **Deployment Notes**: Any special deployment considerations

Format the response in clear markdown with appropriate headings."""

        # Send prompt to Gemini web interface
        response = self.send_prompt_to_gemini_web(prompt)
        return response

    def generate_documentation_for_mr(self, project_id: str, mr_iid: str) -> str:
        """
        Generate documentation for a single merge request

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID

        Returns:
            Generated documentation string
        """
        logger.info(f"Processing MR {mr_iid} in project {project_id}")

        # Check MR accessibility first
        accessibility_check = self.check_mr_accessibility(project_id, mr_iid)

        if not accessibility_check['accessible']:
            error_msg = f"MR {project_id}/{mr_iid} is not accessible. Error: {accessibility_check.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return error_msg

        # Get MR information (use from accessibility check if available)
        mr_info = accessibility_check['mr_info']
        if not mr_info:
            mr_info = self.get_merge_request_info(project_id, mr_iid)
            if not mr_info:
                return f"Failed to get MR information for {project_id}/{mr_iid}"

        # Get MR changes (only if API accessible)
        java_changes = []
        if accessibility_check['api_accessible']:
            changes_data = self.get_merge_request_changes(project_id, mr_iid)
            if changes_data:
                java_changes = self.extract_java_changes(changes_data)

        if not java_changes:
            logger.warning(f"No Java changes found in MR {project_id}/{mr_iid}")
            # Continue with basic MR info for documentation
            java_changes = []

        # Generate documentation using Gemini
        documentation = self.analyze_code_changes_with_gemini(java_changes, mr_info)

        return documentation

    def generate_documentation_for_multiple_mrs(self, mr_list: List[Dict]) -> Dict[str, str]:
        """
        Generate documentation for multiple merge requests

        Args:
            mr_list: List of dictionaries with 'project_id' and 'mr_iid' keys

        Returns:
            Dictionary mapping MR identifiers to their documentation
        """
        documentation_results = {}

        # First, check accessibility of all MRs
        logger.info("Checking accessibility of all merge requests...")
        accessible_mrs = []

        for mr in mr_list:
            project_id = mr['project_id']
            mr_iid = mr['mr_iid']
            mr_key = f"{project_id}/{mr_iid}"

            accessibility_check = self.check_mr_accessibility(project_id, mr_iid)

            if accessibility_check['accessible']:
                accessible_mrs.append(mr)
                logger.info(f"✓ MR {mr_key} is accessible")
            else:
                error_msg = f"✗ MR {mr_key} is not accessible: {accessibility_check.get('error', 'Unknown error')}"
                logger.error(error_msg)
                documentation_results[mr_key] = error_msg

        if not accessible_mrs:
            logger.error("No accessible merge requests found!")
            return documentation_results

        logger.info(f"Found {len(accessible_mrs)} accessible MRs out of {len(mr_list)} total")

        # Process accessible MRs
        for mr in accessible_mrs:
            project_id = mr['project_id']
            mr_iid = mr['mr_iid']
            mr_key = f"{project_id}/{mr_iid}"

            try:
                doc = self.generate_documentation_for_mr(project_id, mr_iid)
                documentation_results[mr_key] = doc

                # Add delay to avoid overwhelming the web interface
                time.sleep(5)

            except Exception as e:
                logger.error(f"Error processing MR {mr_key}: {e}")
                documentation_results[mr_key] = f"Error generating documentation: {str(e)}"

        return documentation_results

    def save_documentation_to_file(self, documentation: str, filename: str):
        """
        Save documentation to a file

        Args:
            documentation: Documentation content
            filename: Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(documentation)
            logger.info(f"Documentation saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving documentation: {e}")

    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'driver'):
            self.driver.quit()


# Example usage
def main():
    # Configuration
    GITLAB_URL = "https://gitlab.com"  # Replace with your GitLab URL
    GITLAB_TOKEN = "test123"  # Replace with your GitLab private token

    # List of merge requests to process
    merge_requests = [
        {"project_id": "123", "mr_iid": "45"},
        {"project_id": "124", "mr_iid": "67"},
        {"project_id": "125", "mr_iid": "89"},
        # Add more MRs as needed
    ]

    # Initialize the generator (no Gemini API key needed)
    doc_generator = GitLabMRDocumentationGenerator(
        gitlab_url=GITLAB_URL,
        private_token=GITLAB_TOKEN
    )

    try:
        # Generate documentation for all MRs
        results = doc_generator.generate_documentation_for_multiple_mrs(merge_requests)

        # Save individual documentation files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for mr_key, documentation in results.items():
            filename = f"MR_Documentation_{mr_key.replace('/', '_')}_{timestamp}.md"
            doc_generator.save_documentation_to_file(documentation, filename)

        # Create a combined documentation file
        combined_doc = f"# Merge Request Documentation Report\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for mr_key, documentation in results.items():
            combined_doc += f"## Merge Request: {mr_key}\n\n{documentation}\n\n---\n\n"

        doc_generator.save_documentation_to_file(
            combined_doc,
            f"Combined_MR_Documentation_{timestamp}.md"
        )

        print(f"Documentation generated for {len(results)} merge requests")

    finally:
        # Cleanup
        doc_generator.cleanup()


if __name__ == "__main__":
    main()