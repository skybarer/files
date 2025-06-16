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
import platform
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitLabMRDocumentationGenerator:
    def __init__(self, gitlab_url: str, private_token: str, use_existing_profile: bool = True, 
                 profile_path: str = None, gmail_email: str = None, gmail_password: str = None,
                 gitlab_username: str = None, gitlab_password: str = None):
        """
        Initialize the documentation generator
        
        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.example.com)
            private_token: GitLab private access token
            use_existing_profile: Whether to use existing Chrome profile (default: True)
            profile_path: Custom Chrome profile path (optional)
            gmail_email: Gmail email for authentication (only needed if not using existing profile)
            gmail_password: Gmail password for authentication (only needed if not using existing profile)
            gitlab_username: GitLab username (optional)
            gitlab_password: GitLab password (optional)
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.use_existing_profile = use_existing_profile
        self.profile_path = profile_path
        self.gmail_email = gmail_email
        self.gmail_password = gmail_password
        self.gitlab_username = gitlab_username
        self.gitlab_password = gitlab_password
        self.headers = {'PRIVATE-TOKEN': private_token}
        
        # Authentication status
        self.authenticated_gmail = False
        self.authenticated_gitlab = False
        self.authenticated_gemini = False

        # Setup Chrome driver
        self.setup_chrome_driver()

    def get_default_chrome_profile_path(self) -> str:
        """
        Get the default Chrome profile path based on the operating system
        
        Returns:
            Default Chrome profile path
        """
        system = platform.system()
        
        if system == "Windows":
            # Windows Chrome profile path
            return os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
        elif system == "Darwin":  # macOS
            # macOS Chrome profile path
            return os.path.expanduser("~/Library/Application Support/Google/Chrome")
        elif system == "Linux":
            # Linux Chrome profile path
            return os.path.expanduser("~/.config/google-chrome")
        else:
            logger.warning(f"Unknown operating system: {system}")
            return os.path.expanduser("~/.config/google-chrome")

    def setup_chrome_driver(self):
        """Setup Chrome WebDriver with existing profile or new persistent profile"""
        chrome_options = Options()
        
        # Basic options for better compatibility
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-popup-blocking')

        if self.use_existing_profile:
            # Use existing Chrome profile
            if self.profile_path:
                user_data_dir = self.profile_path
            else:
                user_data_dir = self.get_default_chrome_profile_path()
            
            logger.info(f"Using existing Chrome profile: {user_data_dir}")
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # Optionally specify a profile directory (Default, Profile 1, etc.)
            # chrome_options.add_argument('--profile-directory=Default')
            
        else:
            # Use custom persistent profile directory
            user_data_dir = os.path.expanduser('~/chrome_profile_gitlab_mr')
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
            logger.info(f"Using custom persistent profile: {user_data_dir}")

        # Important: Don't start maximized immediately to avoid conflicts
        # chrome_options.add_argument('--start-maximized')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.maximize_window()
            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            logger.info("Trying fallback without existing profile...")
            
            # Fallback: create new profile
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            fallback_profile = os.path.expanduser('~/chrome_profile_gitlab_mr_fallback')
            chrome_options.add_argument(f'--user-data-dir={fallback_profile}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.maximize_window()
            logger.info("Chrome WebDriver initialized with fallback profile")

    def check_existing_authentications(self) -> Dict[str, bool]:
        """
        Check if user is already authenticated with various services
        
        Returns:
            Dictionary with authentication status for each service
        """
        auth_status = {
            'gmail': False,
            'gitlab': False,
            'gemini': False
        }
        
        try:
            logger.info("Checking existing authentication status...")
            
            # Check Gmail authentication
            logger.info("Checking Gmail authentication...")
            self.driver.get("https://accounts.google.com/")
            time.sleep(3)
            
            try:
                # Look for signs of being logged in
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[@data-gb-custom-button-id='account_switcher']")),
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'profile')]")),
                        EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Google Account']")),
                        EC.url_contains("myaccount.google.com")
                    )
                )
                auth_status['gmail'] = True
                self.authenticated_gmail = True
                logger.info("✅ Gmail: Already authenticated")
            except:
                logger.info("❌ Gmail: Not authenticated")
            
            # Check GitLab authentication
            logger.info("Checking GitLab authentication...")
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.get(f"{self.gitlab_url}/dashboard")
            time.sleep(3)
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[@data-testid='user-menu']")),
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'header-user-avatar')]")),
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@aria-label, 'user menu')]"))
                    )
                )
                auth_status['gitlab'] = True
                self.authenticated_gitlab = True
                logger.info("✅ GitLab: Already authenticated")
            except:
                logger.info("❌ GitLab: Not authenticated")
            
            # Check Gemini authentication
            logger.info("Checking Gemini authentication...")
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.get("https://gemini.google.com/")
            time.sleep(5)
            
            try:
                # Look for Gemini input area
                input_area_xpaths = [
                    "//div[@data-test-id='input-area']",
                    "//div[@contenteditable='true']",
                    "//textarea",
                    "//div[@role='textbox']"
                ]
                
                for xpath in input_area_xpaths:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        auth_status['gemini'] = True
                        self.authenticated_gemini = True
                        logger.info("✅ Gemini: Already authenticated")
                        break
                    except:
                        continue
                
                if not auth_status['gemini']:
                    logger.info("❌ Gemini: Not authenticated or needs setup")
                    
            except:
                logger.info("❌ Gemini: Not authenticated")
            
        except Exception as e:
            logger.error(f"Error checking authentication status: {e}")
        
        return auth_status

    def setup_missing_authentications(self, auth_status: Dict[str, bool]) -> bool:
        """
        Setup missing authentications based on current status
        
        Args:
            auth_status: Current authentication status
            
        Returns:
            True if all authentications are now working, False otherwise
        """
        try:
            # If Gmail is not authenticated, guide user to authenticate manually
            if not auth_status['gmail']:
                logger.info("Gmail authentication required...")
                self.driver.switch_to.window(self.driver.window_handles[0])
                self.driver.get("https://accounts.google.com/signin")
                
                print("\n" + "="*60)
                print("📧 GMAIL AUTHENTICATION REQUIRED")
                print("="*60)
                print("Please complete Gmail authentication in the browser window.")
                print("Once logged in, press Enter to continue...")
                input("Press Enter after completing Gmail authentication: ")
                
                # Verify Gmail authentication
                if self.verify_gmail_authentication():
                    self.authenticated_gmail = True
                    logger.info("✅ Gmail authentication verified")
                else:
                    logger.error("❌ Gmail authentication failed")
                    return False
            
            # If GitLab is not authenticated, guide user to authenticate manually
            if not auth_status['gitlab']:
                logger.info("GitLab authentication required...")
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.get(f"{self.gitlab_url}/users/sign_in")
                
                print("\n" + "="*60)
                print("🦊 GITLAB AUTHENTICATION REQUIRED")
                print("="*60)
                print(f"Please log in to GitLab at: {self.gitlab_url}")
                print("Once logged in, press Enter to continue...")
                input("Press Enter after completing GitLab authentication: ")
                
                # Verify GitLab authentication
                if self.verify_gitlab_authentication():
                    self.authenticated_gitlab = True
                    logger.info("✅ GitLab authentication verified")
                else:
                    logger.error("❌ GitLab authentication failed")
                    return False
            
            # Setup Gemini if not already working
            if not auth_status['gemini']:
                logger.info("Setting up Gemini...")
                if self.setup_gemini_interface():
                    self.authenticated_gemini = True
                    logger.info("✅ Gemini setup completed")
                else:
                    logger.error("❌ Gemini setup failed")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up missing authentications: {e}")
            return False

    def verify_gmail_authentication(self) -> bool:
        """Verify Gmail authentication"""
        try:
            self.driver.get("https://accounts.google.com/")
            time.sleep(3)
            
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[@data-gb-custom-button-id='account_switcher']")),
                    EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'profile')]")),
                    EC.url_contains("myaccount.google.com")
                )
            )
            return True
        except:
            return False

    def verify_gitlab_authentication(self) -> bool:
        """Verify GitLab authentication"""
        try:
            self.driver.get(f"{self.gitlab_url}/dashboard")
            time.sleep(3)
            
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[@data-testid='user-menu']")),
                    EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'header-user-avatar')]")),
                    EC.url_contains("/dashboard")
                )
            )
            return True
        except:
            return False

    def setup_gemini_interface(self) -> bool:
        """Setup Gemini interface"""
        try:
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.get("https://gemini.google.com/")
            time.sleep(5)
            
            # Handle any setup screens
            try:
                setup_buttons = [
                    "//button[contains(text(), 'Try Gemini')]",
                    "//button[contains(text(), 'Get started')]",
                    "//button[contains(text(), 'Continue')]"
                ]
                
                for xpath in setup_buttons:
                    try:
                        button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        button.click()
                        time.sleep(3)
                        break
                    except:
                        continue
            except:
                pass
            
            # Check if input area is available
            input_xpaths = [
                "//div[@data-test-id='input-area']",
                "//div[@contenteditable='true']",
                "//textarea",
                "//div[@role='textbox']"
            ]
            
            for xpath in input_xpaths:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting up Gemini: {e}")
            return False

    def perform_smart_authentication(self) -> bool:
        """
        Perform smart authentication by checking existing sessions first
        
        Returns:
            True if all authentications successful, False otherwise
        """
        logger.info("Starting smart authentication process...")
        
        # Check existing authentication status
        auth_status = self.check_existing_authentications()
        
        # Display current status
        print("\n" + "="*60)
        print("🔐 AUTHENTICATION STATUS")
        print("="*60)
        print(f"Gmail:  {'✅ Authenticated' if auth_status['gmail'] else '❌ Not authenticated'}")
        print(f"GitLab: {'✅ Authenticated' if auth_status['gitlab'] else '❌ Not authenticated'}")
        print(f"Gemini: {'✅ Authenticated' if auth_status['gemini'] else '❌ Not authenticated'}")
        
        # Test GitLab API access
        if self.authenticated_gitlab:
            api_working = self.test_gitlab_api_access()
            print(f"GitLab API: {'✅ Working' if api_working else '❌ Not working'}")
        
        # Setup missing authentications
        all_authenticated = all(auth_status.values())
        
        if not all_authenticated:
            print("\nSome services need authentication...")
            if not self.setup_missing_authentications(auth_status):
                return False
        
        # Final verification
        if not self.test_gitlab_api_access():
            logger.error("GitLab API access failed")
            return False
            
        logger.info("✅ All authentication steps completed successfully!")
        return True

    def test_gitlab_api_access(self) -> bool:
        """Test GitLab API access with the provided token"""
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
                return False

        except Exception as e:
            logger.error(f"Error testing GitLab API access: {e}")
            return False

    # [Rest of the methods remain the same as in the original code]
    # get_merge_request_info, get_merge_request_changes, extract_java_changes,
    # send_prompt_to_gemini_web, etc.

    def get_merge_request_info(self, project_id: str, mr_iid: str) -> Dict:
        """Get merge request information from GitLab API"""
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
        """Get merge request changes from GitLab API"""
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
        """Extract Java file changes from the changes data"""
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
        """Send prompt to Gemini web interface and get response"""
        if not self.authenticated_gemini:
            logger.error("Gemini authentication required")
            return "Error: Gemini not authenticated"

        try:
            logger.info("Sending prompt to Gemini...")
            self.driver.switch_to.window(self.driver.window_handles[0])

            if "gemini.google.com" not in self.driver.current_url:
                self.driver.get("https://gemini.google.com/")
                time.sleep(3)

            # Find input area
            input_element = None
            input_xpaths = [
                "//div[@data-test-id='input-area']",
                "//div[@contenteditable='true']",
                "//textarea",
                "//div[@role='textbox']"
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

            # Clear and enter prompt
            input_element.click()
            time.sleep(1)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.5)
            input_element.send_keys(Keys.DELETE)
            time.sleep(1)

            # Type prompt in chunks
            chunk_size = 1000
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i+chunk_size]
                input_element.send_keys(chunk)
                time.sleep(0.5)

            time.sleep(2)

            # Submit prompt
            send_xpaths = [
                "//button[@data-test-id='send-button']",
                "//button[contains(@aria-label, 'Send')]",
                "//button[contains(@title, 'Send')]"
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
            else:
                input_element.send_keys(Keys.ENTER)

            logger.info("Prompt submitted, waiting for response...")
            time.sleep(5)

            # Wait for response (simplified)
            max_wait_time = 180
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    response_text = self.extract_gemini_response()
                    if response_text and len(response_text) > 100:
                        return response_text
                    time.sleep(3)
                except:
                    time.sleep(3)

            return "Response timeout or not found"

        except Exception as e:
            logger.error(f"Error sending prompt to Gemini: {e}")
            return f"Error getting response from Gemini: {str(e)}"

    def extract_gemini_response(self) -> str:
        """Extract response from Gemini web interface"""
        try:
            response_xpaths = [
                "//div[@data-test-id='response']",
                "//div[contains(@class, 'response-content')]",
                "//div[contains(@class, 'message-content')]"
            ]

            for xpath in response_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        response_text = elements[-1].text.strip()
                        if response_text and len(response_text) > 50:
                            return response_text
                except:
                    continue

            # Fallback: get page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = page_text.split('\n')
            
            # Look for meaningful response content
            for i, line in enumerate(lines):
                if any(keyword in line.lower() for keyword in ['summary', 'analysis', 'changes']):
                    return '\n'.join(lines[i:i+50])  # Return next 50 lines
            
            return page_text[-2000:] if page_text else "No response found"

        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return "Error extracting response"

    def analyze_code_changes_with_gemini(self, java_changes: List[Dict], mr_info: Dict) -> str:
        """Analyze Java code changes using Gemini web interface"""
        if not self.authenticated_gemini:
            return "Error: Gemini authentication required"

        # Create comprehensive prompt
        prompt = f"""Please analyze the following GitLab merge request and generate comprehensive documentation.

**Merge Request Information:**
- Title: {mr_info.get('title', 'N/A')}
- Description: {mr_info.get('description', 'N/A')}
- Author: {mr_info.get('author', {}).get('name', 'N/A')}
- Source Branch: {mr_info.get('source_branch', 'N/A')}
- Target Branch: {mr_info.get('target_branch', 'N/A')}

**Java Code Changes ({len(java_changes)} files):**"""

        # Add changes (limit to avoid overly long prompts)
        for i, change in enumerate(java_changes[:3], 1):
            prompt += f"""

**File {i}: {change['file_path']}**
Status: {'New file' if change['new_file'] else 'Modified file'}
```diff
{change['diff'][:1500]}{'...' if len(change['diff']) > 1500 else ''}
```"""

        prompt += """

**Please provide:**
1. **Summary**: Brief overview of changes
2. **Technical Details**: Key modifications per file
3. **Impact Analysis**: System impact and considerations
4. **Risk Assessment**: Potential risks
5. **Testing Recommendations**: Testing suggestions

Format with clear markdown sections."""

        return self.send_prompt_to_gemini_web(prompt)

    def generate_mr_documentation(self, project_id: str, mr_iid: str) -> Dict:
        """Generate complete documentation for a merge request"""
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
        """Save generated documentation to a file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mr_documentation_{documentation_data['project_id']}_{documentation_data['mr_iid']}_{timestamp}.md"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Merge Request Documentation\n\n")
                f.write(f"**Project ID:** {documentation_data['project_id']}\n")
                f.write(f"**MR IID:** {documentation_data['mr_iid']}\n")
                f.write(f"**Generated:** {documentation_data['generated_at']}\n\n")

                mr_info = documentation_data['mr_info']
                f.write("## Merge Request Details\n\n")
                f.write(f"- **Title:** {mr_info.get('title', 'N/A')}\n")
                f.write(f"- **Author:** {mr_info.get('author', {}).get('name', 'N/A')}\n")
                f.write(f"- **Source Branch:** {mr_info.get('source_branch', 'N/A')}\n")
                f.write(f"- **Target Branch:** {mr_info.get('target_branch', 'N/A')}\n")
                f.write(f"- **Status:** {mr_info.get('state', 'N/A')}\n")
                f.write(f"- **Web URL:** {mr_info.get('web_url', 'N/A')}\n\n")

                if mr_info.get('description'):
                    f.write(f"### Description\n\n{mr_info['description']}\n\n")

                f.write("## AI-Generated Analysis\n\n")
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
                print("\n" + "=" * 70)
                print("🚀 GitLab MR Documentation Generator (Smart Profile Mode)")
                print("=" * 70)

                # Perform smart authentication
                print("\n🔐 Step 1: Checking authentication status...")
                if not self.perform_smart_authentication():
                    print("❌ Authentication failed! Please check your credentials.")
                    return

                # Get project and MR details
                print("\n📝 Step 2: Enter merge request details")
                project_id = input("Enter GitLab project ID: ").strip()
                mr_iid = input("Enter Merge Request IID: ").strip()

                if not project_id or not mr_iid:
                    print("❌ Project ID and MR IID are required!")
                    return

                # Generate documentation
                print("\n🔄 Step 3: Generating documentation...")
                print("This may take a few minutes as we analyze the code changes...")

                documentation_data = self.generate_mr_documentation(project_id, mr_iid)

                if "error" in documentation_data:
                    print(f"❌ Error: {documentation_data['error']}")
                    return

                # Save documentation
                print("\n💾 Step 4: Saving documentation...")
                output_file = self.save_documentation_to_file(documentation_data)

                if output_file:
                    print(f"✅ Documentation generated successfully!")
                    print(f"📄 File saved as: {output_file}")

                    # Show preview
                    print("\n📖 Preview:")
                    print("-" * 50)
                    preview = documentation_data['documentation'][:500]
                    print(f"{preview}...")
                    print("-" * 50)
                else:
                    print("❌ Failed to save documentation file")

            except KeyboardInterrupt:
                print("\n\n⚠️ Operation cancelled by user")
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"❌ An error occurred: {str(e)}")
            finally:
                print("\n🧹 Cleaning up...")
                self.cleanup()

def main():
    """Main function to run the documentation generator"""
    import argparse

    parser = argparse.ArgumentParser(
        description="GitLab MR Documentation Generator with Smart Authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode with existing Chrome profile
  python gitlab_mr_existing_profile.py

  # Command line mode
  python gitlab_mr_existing_profile.py --project-id 123 --mr-iid 45 --gitlab-url https://gitlab.company.com --token your_token

  # Using custom Chrome profile path
  python gitlab_mr_existing_profile.py --profile-path "/path/to/chrome/profile"

  # Force new profile (don't use existing)
  python gitlab_mr_existing_profile.py --no-existing-profile
        """
    )

    parser.add_argument(
        '--gitlab-url',
        required=False,
        help='GitLab instance URL (e.g., https://gitlab.example.com)'
    )

    parser.add_argument(
        '--token',
        required=False,
        help='GitLab private access token'
    )

    parser.add_argument(
        '--project-id',
        required=False,
        help='GitLab project ID'
    )

    parser.add_argument(
        '--mr-iid',
        required=False,
        help='Merge Request IID'
    )

    parser.add_argument(
        '--profile-path',
        required=False,
        help='Custom Chrome profile path'
    )

    parser.add_argument(
        '--no-existing-profile',
        action='store_true',
        help='Don\'t use existing Chrome profile, create new one'
    )

    parser.add_argument(
        '--output-file',
        required=False,
        help='Output file path for documentation'
    )

    args = parser.parse_args()

    # Get required parameters
    gitlab_url = args.gitlab_url
    private_token = args.token

    # Interactive input if not provided via command line
    if not gitlab_url:
        print("🔧 GitLab Configuration")
        gitlab_url = input("Enter your GitLab URL (e.g., https://gitlab.example.com): ").strip()

    if not private_token:
        private_token = input("Enter your GitLab private access token: ").strip()

    if not gitlab_url or not private_token:
        print("❌ GitLab URL and private token are required!")
        return

    try:
        # Initialize the generator
        generator = GitLabMRDocumentationGenerator(
            gitlab_url=gitlab_url,
            private_token=private_token,
            use_existing_profile=not args.no_existing_profile,
            profile_path=args.profile_path
        )

        if args.project_id and args.mr_iid:
            # Command line mode
            print(f"\n🚀 Generating documentation for MR {args.mr_iid} in project {args.project_id}")

            # Perform authentication
            if not generator.perform_smart_authentication():
                print("❌ Authentication failed!")
                return

            # Generate documentation
            documentation_data = generator.generate_mr_documentation(args.project_id, args.mr_iid)

            if "error" in documentation_data:
                print(f"❌ Error: {documentation_data['error']}")
                return

            # Save documentation
            output_file = generator.save_documentation_to_file(documentation_data, args.output_file)

            if output_file:
                print(f"✅ Documentation saved to: {output_file}")
            else:
                print("❌ Failed to save documentation")
        else:
            # Interactive mode
            generator.run_interactive_mode()

    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()