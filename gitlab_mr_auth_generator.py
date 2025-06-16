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
    def __init__(self, gitlab_url: str, private_token: str, gmail_email: str = None):
        """
        Initialize the documentation generator
        
        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.example.com)
            private_token: GitLab private access token
            gmail_email: Gmail email for authentication (optional)
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.gmail_email = gmail_email
        self.headers = {'PRIVATE-TOKEN': private_token}
        self.authenticated_gmail = False
        self.authenticated_gitlab = False
        self.authenticated_gemini = False
        
        # Setup Chrome driver
        self.setup_chrome_driver()
    
    def setup_chrome_driver(self):
        """Setup Chrome WebDriver with appropriate options for authentication"""
        chrome_options = Options()
        # Don't use headless mode for authentication
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use persistent user data directory to maintain sessions
        user_data_dir = os.path.expanduser('~/chrome_profile_gitlab_mr')
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        
        # Additional arguments for better compatibility
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-extensions')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.maximize_window()
        
        logger.info("Chrome WebDriver initialized with persistent profile")
    
    def authenticate_gmail(self) -> bool:
        """
        Authenticate with Gmail/Google account
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Starting Gmail authentication...")
            self.driver.get("https://accounts.google.com")
            
            # Check if already logged in
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-gb-custom-button-id='account_switcher']"))
                )
                logger.info("Already logged into Google account")
                self.authenticated_gmail = True
                return True
            except:
                pass
            
            # If not logged in, wait for manual login
            logger.info("Please log in to your Google account manually in the browser window")
            logger.info("The script will wait for you to complete the login process...")
            
            input("Press Enter after you have successfully logged into Gmail/Google account...")
            
            # Verify login by checking for account elements
            try:
                self.driver.get("https://accounts.google.com")
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-gb-custom-button-id='account_switcher']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt*='profile']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Google Account']"))
                    )
                )
                logger.info("Gmail authentication successful!")
                self.authenticated_gmail = True
                return True
                
            except Exception as e:
                logger.error(f"Gmail authentication verification failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error during Gmail authentication: {e}")
            return False
    
    def authenticate_gitlab(self) -> bool:
        """
        Authenticate with GitLab (web interface)
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Starting GitLab web authentication...")
            self.driver.get(f"{self.gitlab_url}/users/sign_in")
            
            # Check if already logged in by looking for user menu or dashboard
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='user-menu']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".header-user-avatar")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='user menu']")),
                        EC.url_contains("/dashboard")
                    )
                )
                logger.info("Already logged into GitLab")
                self.authenticated_gitlab = True
                return True
            except:
                pass
            
            # If not logged in, wait for manual login
            logger.info(f"Please log in to GitLab ({self.gitlab_url}) manually in the browser window")
            logger.info("The script will wait for you to complete the login process...")
            
            input("Press Enter after you have successfully logged into GitLab...")
            
            # Verify login by checking for user elements or dashboard
            try:
                # Go to dashboard to verify login
                self.driver.get(f"{self.gitlab_url}/dashboard")
                
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='user-menu']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".header-user-avatar")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='user menu']")),
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
            logger.error(f"Error during GitLab authentication: {e}")
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
            
            self.driver.get("https://gemini.google.com/")
            
            # Wait for page to load
            time.sleep(5)
            
            # Check if we can access Gemini (look for input area)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='input-area']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']")),
                        EC.presence_of_element_located((By.TAG_NAME, "textarea")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[role='textbox']"))
                    )
                )
                logger.info("Gemini interface is ready!")
                self.authenticated_gemini = True
                return True
                
            except Exception as e:
                logger.warning("Gemini interface might need additional setup or acceptance of terms")
                logger.info("Please complete any required setup in the Gemini interface")
                input("Press Enter after Gemini interface is ready (you can see the chat input)...")
                
                # Verify again
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='input-area']")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']")),
                            EC.presence_of_element_located((By.TAG_NAME, "textarea")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='textbox']"))
                        )
                    )
                    logger.info("Gemini interface verified and ready!")
                    self.authenticated_gemini = True
                    return True
                except:
                    logger.error("Could not verify Gemini interface readiness")
                    return False
                
        except Exception as e:
            logger.error(f"Error setting up Gemini interface: {e}")
            return False
    
    def perform_full_authentication(self) -> bool:
        """
        Perform complete authentication flow
        
        Returns:
            True if all authentications successful, False otherwise
        """
        logger.info("Starting full authentication process...")
        
        # Step 1: Authenticate Gmail
        if not self.authenticate_gmail():
            logger.error("Gmail authentication failed")
            return False
        
        # Step 2: Authenticate GitLab web interface
        if not self.authenticate_gitlab():
            logger.error("GitLab web authentication failed")
            return False
        
        # Step 3: Test GitLab API access
        if not self.test_gitlab_api_access():
            logger.error("GitLab API access failed")
            return False
        
        # Step 4: Setup Gemini interface
        if not self.setup_gemini_web_interface():
            logger.error("Gemini interface setup failed")
            return False
        
        logger.info("All authentication steps completed successfully!")
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
            
            # Make sure we're on Gemini page
            if "gemini.google.com" not in self.driver.current_url:
                self.driver.get("https://gemini.google.com/")
                time.sleep(3)
            
            # Find the input area
            input_selectors = [
                "[data-test-id='input-area']",
                "div[contenteditable='true']",
                "textarea",
                ".ql-editor",
                "[role='textbox']",
                "div[aria-label*='Message']",
                "div[aria-label*='prompt']"
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
            
            # Submit the prompt
            time.sleep(2)
            
            # Try different submission methods
            try:
                input_element.send_keys(Keys.ENTER)
            except:
                try:
                    send_button = self.driver.find_element(By.CSS_SELECTOR, 
                        "[data-test-id='send-button'], button[aria-label*='Send'], button[title*='Send']")
                    send_button.click()
                except:
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
            
            logger.info("Prompt submitted, waiting for response...")
            
            # Wait for response
            time.sleep(5)
            
            # Wait for response to complete
            max_wait_time = 180  # 3 minutes max
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    # Check for loading indicators
                    loading_indicators = self.driver.find_elements(By.CSS_SELECTOR, 
                        ".loading, .generating, [data-test-id='loading'], .spinner")
                    
                    if not loading_indicators:
                        # Look for response content
                        response_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                            "[data-test-id='response'], .response-content, .message-content")
                        
                        if response_elements and response_elements[-1].text.strip():
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
        """Extract response from Gemini web interface"""
        try:
            response_selectors = [
                "[data-test-id='response']",
                ".response-content",
                ".message-content",
                ".model-response",
                "div[role='presentation'] div[data-test-id]",
                ".conversation-turn:last-child",
            ]
            
            for selector in response_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
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
        
        # Get MR information
        mr_info = self.get_merge_request_info(project_id, mr_iid)
        if not mr_info:
            return f"Failed to get MR information for {project_id}/{mr_iid}"
        
        # Get MR changes
        changes_data = self.get_merge_request_changes(project_id, mr_iid)
        if not changes_data:
            return f"Failed to get MR changes for {project_id}/{mr_iid}"
        
        # Extract Java changes
        java_changes = self.extract_java_changes(changes_data)
        if not java_changes:
            return f"No Java changes found in MR {project_id}/{mr_iid}"
        
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
        
        for mr in mr_list:
            project_id = mr['project_id']
            mr_iid = mr['mr_iid']
            mr_key = f"{project_id}/{mr_iid}"
            
            try:
                doc = self.generate_documentation_for_mr(project_id, mr_iid)
                documentation_results[mr_key] = doc
                
                # Add delay to avoid rate limiting
                time.sleep(2)
                
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

# Example usage with authentication
def main():
    # Configuration
    GITLAB_URL = "https://your-gitlab-instance.com"  # Replace with your GitLab URL
    GITLAB_TOKEN = "your-private-token"  # Replace with your GitLab private token
    GMAIL_EMAIL = "your-email@gmail.com"  # Optional: your Gmail email
    
    # List of merge requests to process
    merge_requests = [
        {"project_id": "123", "mr_iid": "45"},
        {"project_id": "124", "mr_iid": "67"},
        {"project_id": "125", "mr_iid": "89"},
        # Add more MRs as needed
    ]
    
    # Initialize the generator
    doc_generator = GitLabMRDocumentationGenerator(
        gitlab_url=GITLAB_URL,
        private_token=GITLAB_TOKEN,
        gmail_email=GMAIL_EMAIL
    )
    
    try:
        # Perform complete authentication
        if not doc_generator.perform_full_authentication():
            logger.error("Authentication failed. Cannot proceed.")
            return
        
        logger.info("All authentications successful! Proceeding with documentation generation...")
        
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
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        
    finally:
        # Cleanup
        doc_generator.cleanup()

if __name__ == "__main__":
    main()