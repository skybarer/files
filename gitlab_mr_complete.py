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
    def __init__(self, gitlab_url: str, private_token: str, gmail_email: str, gmail_password: str,
                 gitlab_username: str = None, gitlab_password: str = None):
        """
        Initialize the documentation generator
        
        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.example.com)
            private_token: GitLab private access token
            gmail_email: Gmail email for authentication
            gmail_password: Gmail password for authentication
            gitlab_username: GitLab username (optional, for credential-based login)
            gitlab_password: GitLab password (optional, for credential-based login)
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.gmail_email = gmail_email
        self.gmail_password = gmail_password
        self.gitlab_username = gitlab_username
        self.gitlab_password = gitlab_password
        self.headers = {'PRIVATE-TOKEN': private_token}
        self.authenticated_gmail = False
        self.authenticated_gitlab = False
        self.authenticated_gemini = False

        # Setup Chrome driver
        self.setup_chrome_driver()

    def setup_chrome_driver(self):
        """Setup Chrome WebDriver with appropriate options for automatic authentication"""
        chrome_options = Options()
        # Don't use headless mode for authentication debugging
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Use persistent user data directory
        user_data_dir = os.path.expanduser('~/chrome_profile_gitlab_mr')
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')

        # Additional arguments for better compatibility
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.maximize_window()

        logger.info("Chrome WebDriver initialized with persistent profile")

    def authenticate_gmail_auto(self) -> bool:
        """
        Automatically authenticate with Gmail using provided credentials
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Starting automatic Gmail authentication...")
            self.driver.get("https://accounts.google.com/signin")

            # Wait for page to load
            time.sleep(3)

            # Check if already logged in
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[@data-gb-custom-button-id='account_switcher']")),
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'profile')]")),
                        EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Google Account']"))
                    )
                )
                logger.info("Already logged into Google account")
                self.authenticated_gmail = True
                return True
            except:
                pass

            # Find email input field using multiple XPath strategies
            email_input = None
            email_xpaths = [
                "//input[@type='email']",
                "//input[@id='identifierId']",
                "//input[@name='identifier']",
                "//input[@aria-label='Email or phone']",
                "//input[contains(@placeholder, 'Email')]"
            ]

            for xpath in email_xpaths:
                try:
                    email_input = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not email_input:
                logger.error("Could not find email input field")
                return False

            # Clear and enter email
            email_input.clear()
            email_input.send_keys(self.gmail_email)
            time.sleep(1)

            # Find and click Next button
            next_button = None
            next_xpaths = [
                "//button[@id='identifierNext']",
                "//button[contains(text(), 'Next')]",
                "//button[@type='submit']",
                "//div[@id='identifierNext']//button",
                "//span[text()='Next']/../.."
            ]

            for xpath in next_xpaths:
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not next_button:
                logger.error("Could not find Next button")
                return False

            next_button.click()
            time.sleep(3)

            # Wait for password page and enter password
            password_input = None
            password_xpaths = [
                "//input[@type='password']",
                "//input[@name='password']",
                "//input[@aria-label='Enter your password']",
                "//input[contains(@placeholder, 'password')]"
            ]

            for xpath in password_xpaths:
                try:
                    password_input = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not password_input:
                logger.error("Could not find password input field")
                return False

            # Clear and enter password
            password_input.clear()
            password_input.send_keys(self.gmail_password)
            time.sleep(1)

            # Find and click Next button for password
            password_next_button = None
            password_next_xpaths = [
                "//button[@id='passwordNext']",
                "//button[contains(text(), 'Next')]",
                "//button[@type='submit']",
                "//div[@id='passwordNext']//button",
                "//span[text()='Next']/../.."
            ]

            for xpath in password_next_xpaths:
                try:
                    password_next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not password_next_button:
                logger.error("Could not find password Next button")
                return False

            password_next_button.click()
            time.sleep(5)

            # Handle 2FA if required
            try:
                # Check for 2FA prompts
                two_fa_elements = self.driver.find_elements(By.XPATH,
                    "//div[contains(text(), 'verify') or contains(text(), '2-Step') or contains(text(), 'phone')]")

                if two_fa_elements:
                    logger.warning("2FA verification required. Please complete it manually.")
                    input("Press Enter after completing 2FA verification...")
            except:
                pass

            # Verify successful login
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.url_contains("myaccount.google.com"),
                        EC.presence_of_element_located((By.XPATH, "//div[@data-gb-custom-button-id='account_switcher']")),
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'profile')]"))
                    )
                )
                logger.info("Gmail authentication successful!")
                self.authenticated_gmail = True
                return True

            except Exception as e:
                logger.error(f"Gmail authentication verification failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Error during automatic Gmail authentication: {e}")
            return False

    def authenticate_gitlab_auto(self) -> bool:
        """
        Automatically authenticate with GitLab using tabs and credentials
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Starting automatic GitLab authentication...")

            # Open GitLab in a new tab
            self.driver.execute_script("window.open('');")

            # Switch to the new tab (second tab)
            self.driver.switch_to.window(self.driver.window_handles[1])

            # Navigate to GitLab login page
            self.driver.get(f"{self.gitlab_url}/users/sign_in")
            time.sleep(3)

            # Check if already logged in
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[@data-testid='user-menu']")),
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'header-user-avatar')]")),
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@aria-label, 'user menu')]")),
                        EC.url_contains("/dashboard")
                    )
                )
                logger.info("Already logged into GitLab")
                self.authenticated_gitlab = True
                return True
            except:
                pass

            # Find username/email input field
            username_input = None
            username_xpaths = [
                "//input[@id='user_login']",
                "//input[@name='user[login]']",
                "//input[@type='email']",
                "//input[@placeholder='Username or email']",
                "//input[contains(@class, 'form-control') and (@type='text' or @type='email')]"
            ]

            for xpath in username_xpaths:
                try:
                    username_input = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not username_input:
                logger.error("Could not find GitLab username input field")
                return False

            # Clear and enter username
            username_input.clear()
            username_input.send_keys(self.gitlab_username or self.gmail_email)
            time.sleep(1)

            # Find password input field
            password_input = None
            password_xpaths = [
                "//input[@id='user_password']",
                "//input[@name='user[password]']",
                "//input[@type='password']",
                "//input[@placeholder='Password']"
            ]

            for xpath in password_xpaths:
                try:
                    password_input = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not password_input:
                logger.error("Could not find GitLab password input field")
                return False

            # Clear and enter password
            password_input.clear()
            password_input.send_keys(self.gitlab_password)
            time.sleep(1)

            # Find and click sign in button
            signin_button = None
            signin_xpaths = [
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//button[contains(text(), 'Sign in')]",
                "//input[@value='Sign in']",
                "//button[@data-testid='sign-in-button']"
            ]

            for xpath in signin_xpaths:
                try:
                    signin_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

            if not signin_button:
                logger.error("Could not find GitLab sign in button")
                return False

            signin_button.click()
            time.sleep(5)

            # Handle potential 2FA or additional verification
            try:
                # Check for 2FA or other verification prompts
                verification_elements = self.driver.find_elements(By.XPATH,
                    "//div[contains(text(), 'verify') or contains(text(), '2FA') or contains(text(), 'code')]")

                if verification_elements:
                    logger.warning("Additional verification required. Please complete it manually.")
                    input("Press Enter after completing verification...")
            except:
                pass

            # Verify successful login
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[@data-testid='user-menu']")),
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'header-user-avatar')]")),
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@aria-label, 'user menu')]")),
                        EC.url_contains("/dashboard")
                    )
                )

                logger.info("GitLab authentication successful!")
                self.authenticated_gitlab = True
                return True

            except Exception as e:
                logger.error(f"GitLab authentication verification failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Error during automatic GitLab authentication: {e}")
            return False

    def test_gitlab_api_access(self) -> bool:
        """
        Test GitLab API access with the provided token
        
        Returns:
            True if API access is working, False otherwise
        """
        try:
            logger.info("Testing GitLab API access...")
            url = f"{self.gitlab_url}/api/v4/user"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"GitLab API access successful! User: {user_info.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"GitLab API access failed with status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error testing GitLab API access: {e}")
            return False

    def setup_gemini_web_interface(self) -> bool:
        """
        Setup Gemini web interface after Gmail authentication
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info("Setting up Gemini web interface...")

            if not self.authenticated_gmail:
                logger.error("Gmail authentication required before accessing Gemini")
                return False

            # Switch back to first tab or create new tab for Gemini
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[0])
            else:
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[0])

            self.driver.get("https://gemini.google.com/")
            time.sleep(5)

            # Check for terms acceptance or setup screens
            try:
                # Look for "Try Gemini" or similar buttons
                try_gemini_xpaths = [
                    "//button[contains(text(), 'Try Gemini')]",
                    "//button[contains(text(), 'Get started')]",
                    "//button[contains(text(), 'Continue')]",
                    "//a[contains(text(), 'Try Gemini')]"
                ]

                for xpath in try_gemini_xpaths:
                    try:
                        try_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        try_button.click()
                        time.sleep(3)
                        break
                    except:
                        continue
            except:
                pass

            # Check if we can access Gemini interface
            try:
                input_area_xpaths = [
                    "//div[@data-test-id='input-area']",
                    "//div[@contenteditable='true']",
                    "//textarea",
                    "//div[@role='textbox']",
                    "//div[contains(@aria-label, 'Message')]",
                    "//div[contains(@placeholder, 'Enter a prompt')]"
                ]

                input_element = None
                for xpath in input_area_xpaths:
                    try:
                        input_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        break
                    except:
                        continue

                if input_element:
                    logger.info("Gemini interface is ready!")
                    self.authenticated_gemini = True
                    return True
                else:
                    logger.warning("Gemini interface might need additional setup")
                    return False

            except Exception as e:
                logger.error(f"Could not access Gemini interface: {e}")
                return False

        except Exception as e:
            logger.error(f"Error setting up Gemini interface: {e}")
            return False

    def perform_full_authentication(self) -> bool:
        """
        Perform complete automatic authentication flow
        
        Returns:
            True if all authentications successful, False otherwise
        """
        logger.info("Starting automatic authentication process...")

        # Step 1: Authenticate Gmail automatically
        if not self.authenticate_gmail_auto():
            logger.error("Automatic Gmail authentication failed")
            return False

        # Step 2: Authenticate GitLab automatically (in second tab)
        if not self.authenticate_gitlab_auto():
            logger.error("Automatic GitLab authentication failed")
            return False

        # Step 3: Test GitLab API access
        if not self.test_gitlab_api_access():
            logger.error("GitLab API access failed")
            return False

        # Step 4: Setup Gemini interface
        if not self.setup_gemini_web_interface():
            logger.error("Gemini interface setup failed")
            return False

        logger.info("All automatic authentication steps completed successfully!")
        return True

    def get_merge_request_info(self, project_id: str, mr_iid: str) -> Dict:
        """
        Get merge request information from GitLab API
        
        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID
            
        Returns:
            Dictionary containing MR information
        """
        if not self.authenticated_gitlab:
            logger.error("GitLab authentication required")
            return None

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
        if not self.authenticated_gitlab:
            logger.error("GitLab authentication required")
            return None

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

    def send_prompt_to_gemini_web(self, prompt: str) -> str:
        """
        Send prompt to Gemini web interface and get response
        
        Args:
            prompt: The prompt to send to Gemini
            
        Returns:
            Gemini's response as string
        """
        if not self.authenticated_gemini:
            logger.error("Gemini authentication required")
            return "Error: Gemini not authenticated"

        try:
            logger.info("Sending prompt to Gemini...")

            # Switch to Gemini tab (first tab)
            self.driver.switch_to.window(self.driver.window_handles[0])

            # Make sure we're on Gemini page
            if "gemini.google.com" not in self.driver.current_url:
                self.driver.get("https://gemini.google.com/")
                time.sleep(3)

            # Find the input area using XPath
            input_element = None
            input_xpaths = [
                "//div[@data-test-id='input-area']",
                "//div[@contenteditable='true']",
                "//textarea",
                "//div[@role='textbox']",
                "//div[contains(@aria-label, 'Message')]",
                "//div[contains(@placeholder, 'Enter a prompt')]"
            ]

            for xpath in input_xpaths:
                try:
                    input_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    break
                except:
                    continue

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

            # Type the prompt in chunks
            chunk_size = 1000
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i+chunk_size]
                input_element.send_keys(chunk)
                time.sleep(0.5)

            # Submit the prompt using XPath
            time.sleep(2)

            # Find and click send button
            send_button = None
            send_xpaths = [
                "//button[@data-test-id='send-button']",
                "//button[contains(@aria-label, 'Send')]",
                "//button[contains(@title, 'Send')]",
                "//button[contains(text(), 'Send')]",
                "//button[@type='submit']"
            ]

            for xpath in send_xpaths:
                try:
                    send_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    send_button.click()
                    break
                except:
                    continue

            if not send_button:
                # Fallback to Enter key
                input_element.send_keys(Keys.ENTER)

            logger.info("Prompt submitted, waiting for response...")

            # Wait for response
            time.sleep(5)

            # Wait for response to complete
            max_wait_time = 180  # 3 minutes max
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                try:
                    # Check for loading indicators
                    loading_xpaths = [
                        "//div[contains(@class, 'loading')]",
                        "//div[contains(@class, 'generating')]",
                        "//div[@data-test-id='loading']",
                        "//div[contains(@class, 'spinner')]"
                    ]

                    loading_indicators = []
                    for xpath in loading_xpaths:
                        loading_indicators.extend(self.driver.find_elements(By.XPATH, xpath))

                    if not loading_indicators:
                        # Look for response content
                        response_xpaths = [
                            "//div[@data-test-id='response']",
                            "//div[contains(@class, 'response-content')]",
                            "//div[contains(@class, 'message-content')]"
                        ]

                        for xpath in response_xpaths:
                            response_elements = self.driver.find_elements(By.XPATH, xpath)
                            if response_elements and response_elements[-1].text.strip():
                                break
                        else:
                            time.sleep(3)
                            continue
                        break

                    time.sleep(3)
                except:
                    time.sleep(3)

            # Extract the response
            response_text = self.extract_gemini_response()

            if not response_text:
                logger.warning("No response text found, trying alternative extraction")
                response_text = self.extract_gemini_response_alternative()

            return response_text

        except Exception as e:
            logger.error(f"Error sending prompt to Gemini: {e}")
            return f"Error getting response from Gemini: {str(e)}"

    def extract_gemini_response(self) -> str:
        """Extract response from Gemini web interface using XPath"""
        try:
            response_xpaths = [
                "//div[@data-test-id='response']",
                "//div[contains(@class, 'response-content')]",
                "//div[contains(@class, 'message-content')]",
                "//div[contains(@class, 'model-response')]",
                "//div[@role='presentation']//div[@data-test-id]",
                "//div[contains(@class, 'conversation-turn')][last()]"
            ]

            for xpath in response_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        response_element = elements[-1]
                        response_text = response_element.text.strip()
                        if response_text and len(response_text) > 50:
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
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = page_text.split('\n')
            response_lines = []
            found_response = False

            for line in lines:
                if any(keyword in line.lower() for keyword in ['summary', 'technical changes', 'impact analysis']):
                    found_response = True

                if found_response:
                    response_lines.append(line)

            return '\n'.join(response_lines) if response_lines else page_text[-2000:]

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
        if not self.authenticated_gemini:
            return "Error: Gemini authentication required"

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
        for i, change in enumerate(java_changes[:5], 1):
            prompt += f"""

**File {i}: {change['file_path']}**
- Status: {'New file' if change['new_file'] else 'Deleted file' if change['deleted_file'] else 'Renamed file' if change['renamed_file'] else 'Modified file'}
- Old path: {change['old_path']}

**Changes:**
```diff
{change['diff'][:2000]}{'...' if len(change['diff']) > 2000 else ''}
```"""

        prompt += """

**Please provide a comprehensive analysis including:**

1. **Summary**: Brief overview of what this merge request accomplishes
2. **Technical Changes**: Detailed breakdown of changes made to each Java file
3. **Impact Analysis**: Potential impact on the system, performance, or other components
4. **Risk Assessment**: Any potential risks or concerns with these changes
5. **Testing Recommendations**: Suggestions for testing these changes
6. **Documentation Updates**: Any documentation that might need to be updated

Please format your response in clear sections with markdown formatting."""

        # Send prompt to Gemini and get response
        return self.send_prompt_to_gemini_web(prompt)

    def generate_mr_documentation(self, project_id: str, mr_iid: str) -> Dict:
        """
        Generate complete documentation for a merge request

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID

        Returns:
            Dictionary containing the generated documentation
        """
        logger.info(f"Generating documentation for MR {mr_iid} in project {project_id}")

        # Get MR information
        mr_info = self.get_merge_request_info(project_id, mr_iid)
        if not mr_info:
            return {"error": "Failed to get merge request information"}

        # Get MR changes
        changes_data = self.get_merge_request_changes(project_id, mr_iid)
        if not changes_data:
            return {"error": "Failed to get merge request changes"}

        # Extract Java changes
        java_changes = self.extract_java_changes(changes_data)
        if not java_changes:
            return {"error": "No Java file changes found in this merge request"}

        logger.info(f"Found {len(java_changes)} Java file changes")

        # Analyze with Gemini
        documentation = self.analyze_code_changes_with_gemini(java_changes, mr_info)

        return {
            "project_id": project_id,
            "mr_iid": mr_iid,
            "mr_info": mr_info,
            "java_changes_count": len(java_changes),
            "documentation": documentation,
            "generated_at": datetime.now().isoformat()
        }

    def save_documentation_to_file(self, documentation_data: Dict, output_file: str = None) -> str:
        """
        Save generated documentation to a file

        Args:
            documentation_data: Documentation data dictionary
            output_file: Output file path (optional)

        Returns:
            Path to the saved file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mr_documentation_{documentation_data['project_id']}_{documentation_data['mr_iid']}_{timestamp}.md"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Merge Request Documentation\n\n")
                f.write(f"**Project ID:** {documentation_data['project_id']}\n")
                f.write(f"**MR IID:** {documentation_data['mr_iid']}\n")
                f.write(f"**Generated:** {documentation_data['generated_at']}\n\n")

                mr_info = documentation_data['mr_info']
                f.write(f"## Merge Request Details\n\n")
                f.write(f"- **Title:** {mr_info.get('title', 'N/A')}\n")
                f.write(f"- **Author:** {mr_info.get('author', {}).get('name', 'N/A')}\n")
                f.write(f"- **Source Branch:** {mr_info.get('source_branch', 'N/A')}\n")
                f.write(f"- **Target Branch:** {mr_info.get('target_branch', 'N/A')}\n")
                f.write(f"- **Status:** {mr_info.get('state', 'N/A')}\n")
                f.write(f"- **Created:** {mr_info.get('created_at', 'N/A')}\n")
                f.write(f"- **Web URL:** {mr_info.get('web_url', 'N/A')}\n\n")

                if mr_info.get('description'):
                    f.write(f"### Description\n\n{mr_info['description']}\n\n")

                f.write(f"## AI-Generated Analysis\n\n")
                f.write(f"**Java Files Changed:** {documentation_data['java_changes_count']}\n\n")
                f.write(documentation_data['documentation'])

            logger.info(f"Documentation saved to: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
            return ""

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def run_interactive_mode(self):
        """Run the tool in interactive mode"""
        try:
            print("\n" + "=" * 60)
            print("GitLab MR Documentation Generator")
            print("=" * 60)

            # Perform authentication
            print("\nStep 1: Performing automatic authentication...")
            if not self.perform_full_authentication():
                print("❌ Authentication failed! Please check your credentials.")
                return

            print("✅ All authentication steps completed successfully!")

            # Get project and MR details
            print("\nStep 2: Enter merge request details")
            project_id = input("Enter GitLab project ID: ").strip()
            mr_iid = input("Enter merge request IID: ").strip()

            if not project_id or not mr_iid:
                print("❌ Project ID and MR IID are required!")
                return

            # Generate documentation
            print(f"\nStep 3: Generating documentation for MR {mr_iid} in project {project_id}...")
            documentation_data = self.generate_mr_documentation(project_id, mr_iid)

            if "error" in documentation_data:
                print(f"❌ Error: {documentation_data['error']}")
                return

            # Save documentation
            print("\nStep 4: Saving documentation...")
            output_file = self.save_documentation_to_file(documentation_data)

            if output_file:
                print(f"✅ Documentation generated successfully!")
                print(f"📄 Saved to: {output_file}")

                # Display summary
                print(f"\n📊 Summary:")
                print(f"   - Java files changed: {documentation_data['java_changes_count']}")
                print(f"   - MR Title: {documentation_data['mr_info'].get('title', 'N/A')}")
                print(f"   - Author: {documentation_data['mr_info'].get('author', {}).get('name', 'N/A')}")
            else:
                print("❌ Failed to save documentation")

        except KeyboardInterrupt:
            print("\n\n⚠️ Process interrupted by user")
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"❌ Unexpected error: {e}")
        finally:
            self.cleanup()


def main():
    """Main function to run the documentation generator"""

    # Configuration - Replace with your actual credentials
    config = {
        'gitlab_url': 'https://gitlab.com',  # Replace with your GitLab URL
        'private_token': 'test123',  # Replace with your GitLab private token
        'gmail_email': 'akashdhar.apssdc@gmail.com',  # Replace with your Gmail email
        'gmail_password': 'test123',  # Replace with your Gmail password
        'gitlab_username': 'your-gitlab-username',  # Replace with your GitLab username (optional)
        'gitlab_password': 'your-gitlab-password'  # Replace with your GitLab password (optional)
    }

    # Validate configuration
    required_fields = ['gitlab_url', 'private_token', 'gmail_email', 'gmail_password']
    missing_fields = [field for field in required_fields if not config[field] or 'your-' in config[field]]

    if missing_fields:
        print("❌ Please configure the following fields in the script:")
        for field in missing_fields:
            print(f"   - {field}")
        print("\nEdit the 'config' dictionary in the main() function with your actual credentials.")
        return

    # Create and run the generator
    generator = GitLabMRDocumentationGenerator(
        gitlab_url=config['gitlab_url'],
        private_token=config['private_token'],
        gmail_email=config['gmail_email'],
        gmail_password=config['gmail_password'],
        gitlab_username=config['gitlab_username'],
        gitlab_password=config['gitlab_password']
    )

    generator.run_interactive_mode()


if __name__ == "__main__":
    main()