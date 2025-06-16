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

# ========================================
# CONFIGURATION SECTION - EDIT THESE VALUES
# ========================================

# GitLab Configuration
GITLAB_URL = "https://your-verizon-gitlab.com"  # Replace with your Verizon GitLab URL
PRIVATE_TOKEN = "your_private_token_here"  # Replace with your GitLab private token

# Merge Requests to Process
MERGE_REQUESTS = [
    {"project_id": "your-project-id", "mr_iid": "123"},
    {"project_id": "your-project-id", "mr_iid": "124"},
    {"project_id": "another-project", "mr_iid": "456"},
    # Add more MRs as needed
]

# Output Configuration
OUTPUT_FILENAME = None  # Set to None for auto-generated filename, or specify like "my_mr_docs.md"

# Advanced Configuration for Private GitLab
SKIP_BROWSER_VERIFICATION = False  # Set to True to skip browser verification and rely on API only
CUSTOM_LOGIN_SELECTORS = []  # Add custom selectors for your Verizon GitLab login page if needed
VERIFICATION_TIMEOUT = 30  # Timeout for verification checks

# ========================================
# END CONFIGURATION SECTION
# ========================================


class GitLabMRDocumentationGenerator:
    def __init__(self, gitlab_url: str, private_token: str):
        """
        Initialize the documentation generator

        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.verizon.com)
            private_token: GitLab private access token
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.headers = {
            'PRIVATE-TOKEN': self.private_token,
            'Content-Type': 'application/json'
        }

        # Initialize session tracking
        self.api_access_working = False
        self.browser_session_available = False
        self.skip_browser = SKIP_BROWSER_VERIFICATION

        # Setup Chrome driver
        self.setup_chrome_driver()

        # Verify GitLab authentication
        self.verify_gitlab_authentication()

        # Initialize Gemini web interface only if browser verification passed
        if not self.skip_browser:
            self.setup_gemini_web_interface()

    def verify_gitlab_authentication(self):
        """Enhanced GitLab authentication verification for private instances"""
        try:
            # Test API access first
            logger.info("Testing GitLab API access...")
            url = f"{self.gitlab_url}/api/v4/user"
            
            # Add timeout and better error handling
            response = requests.get(url, headers=self.headers, timeout=30, verify=True)

            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"✓ GitLab API access verified for user: {user_info.get('name', 'Unknown')} ({user_info.get('username', 'Unknown')})")
                self.api_access_working = True

                # Test project access with first MR to ensure permissions
                if MERGE_REQUESTS:
                    test_project = MERGE_REQUESTS[0]['project_id']
                    self.test_project_access(test_project)

                if not self.skip_browser:
                    self.verify_browser_session_enhanced()
                else:
                    logger.info("Skipping browser verification as configured")
                    self.browser_session_available = False

            elif response.status_code == 401:
                logger.error("GitLab API authentication failed - Invalid token")
                logger.error("Please check your PRIVATE_TOKEN configuration")
                self.handle_api_failure()
            elif response.status_code == 403:
                logger.error("GitLab API access forbidden - Token may lack necessary permissions")
                self.handle_api_failure()
            else:
                logger.warning(f"GitLab API returned status {response.status_code}: {response.text}")
                self.handle_api_failure()

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Error connecting to GitLab: {e}")
            logger.error("This may be due to self-signed certificates in your Verizon GitLab instance")
            self.handle_ssl_error()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to GitLab: {e}")
            logger.error("Please verify the GITLAB_URL is correct and accessible")
            raise
        except Exception as e:
            logger.error(f"Unexpected error verifying GitLab authentication: {e}")
            self.handle_api_failure()

    def test_project_access(self, project_id: str):
        """Test access to a specific project"""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                project_info = response.json()
                logger.info(f"✓ Project access verified: {project_info.get('name', project_id)}")
            elif response.status_code == 404:
                logger.warning(f"Project {project_id} not found - please check project ID")
            elif response.status_code == 403:
                logger.warning(f"Access denied to project {project_id} - check permissions")
            else:
                logger.warning(f"Project access test returned {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Could not test project access: {e}")

    def handle_ssl_error(self):
        """Handle SSL certificate issues common in corporate environments"""
        logger.info("Attempting to continue with SSL verification disabled...")
        
        # Disable SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        try:
            # Retry with SSL verification disabled
            url = f"{self.gitlab_url}/api/v4/user"
            response = requests.get(url, headers=self.headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"✓ GitLab API access verified (SSL disabled): {user_info.get('name', 'Unknown')}")
                self.api_access_working = True
                
                # Update all future requests to disable SSL verification
                self.ssl_verify = False
                
                if not self.skip_browser:
                    self.verify_browser_session_enhanced()
            else:
                self.handle_api_failure()
                
        except Exception as e:
            logger.error(f"Failed even with SSL verification disabled: {e}")
            self.handle_api_failure()

    def handle_api_failure(self):
        """Handle API access failure"""
        logger.warning("GitLab API access failed. Will attempt browser-based access.")
        self.api_access_working = False
        
        if not self.skip_browser:
            self.verify_browser_session_strict()
        else:
            raise Exception("GitLab API access failed and browser verification is disabled")

    def verify_browser_session_enhanced(self):
        """Enhanced browser session verification for private GitLab instances"""
        try:
            logger.info("Verifying browser session with GitLab...")
            self.driver.get(self.gitlab_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, VERIFICATION_TIMEOUT).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            time.sleep(3)  # Additional wait for dynamic content
            
            # Check current URL for redirects (common in corporate SSO)
            current_url = self.driver.current_url
            logger.info(f"Current URL after loading: {current_url}")
            
            # Enhanced login detection for corporate GitLab
            login_indicators = self._detect_login_page()
            
            if login_indicators:
                logger.info("Login page detected. Manual sign-in required.")
                self.prompt_enhanced_signin()
            else:
                # Enhanced authentication verification
                if self._verify_authenticated_session():
                    logger.info("✓ Browser session verified successfully")
                    self.browser_session_available = True
                else:
                    logger.warning("Could not verify authentication status")
                    self.prompt_enhanced_signin()
                    
        except Exception as e:
            logger.error(f"Error verifying browser session: {e}")
            self.prompt_enhanced_signin()

    def _detect_login_page(self) -> bool:
        """Enhanced login page detection for various GitLab configurations"""
        try:
            # Standard GitLab login selectors
            standard_selectors = [
                "input[type='password']",
                "#user_login",
                "#user_password", 
                ".login-form",
                ".sign-in-box",
                ".signin-box"
            ]
            
            # Corporate/SSO login selectors
            corporate_selectors = [
                "input[name='username']",
                "input[name='password']", 
                ".sso-login",
                ".saml-login",
                ".oauth-login",
                "[data-testid='login']",
                ".auth-form",
                ".login-container"
            ]
            
            # Custom selectors from configuration
            all_selectors = standard_selectors + corporate_selectors + CUSTOM_LOGIN_SELECTORS
            
            # Check for login indicators
            for selector in all_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Login indicator found: {selector}")
                    return True
            
            # Check for common login-related text
            login_texts = [
                "sign in", "login", "authenticate", "username", "password",
                "sso", "single sign", "corporate login", "verizon login"
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            for text in login_texts:
                if text in page_text and "dashboard" not in page_text:
                    logger.info(f"Login text indicator found: {text}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"Error detecting login page: {e}")
            return True  # Assume login required if detection fails

    def _verify_authenticated_session(self) -> bool:
        """Enhanced authentication verification"""
        try:
            # Look for authenticated user indicators
            auth_indicators = [
                ".header-user",
                ".user-avatar", 
                ".user-menu",
                ".nav-sidebar",
                ".dashboard",
                ".project-item-select",
                ".navbar-nav",
                "[data-testid='user-menu']",
                ".header-logo + .navbar-nav",  # GitLab-specific structure
                ".user-counter"  # Notification counter indicates logged in user
            ]
            
            for selector in auth_indicators:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Authentication indicator found: {selector}")
                    return True
            
            # Check for dashboard-specific content
            dashboard_texts = ["dashboard", "projects", "groups", "merge requests"]
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            dashboard_count = sum(1 for text in dashboard_texts if text in page_text)
            if dashboard_count >= 2:  # Multiple dashboard indicators
                logger.info("Dashboard content detected - user appears authenticated")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Error verifying authentication: {e}")
            return False

    def prompt_enhanced_signin(self):
        """Enhanced sign-in prompt with better guidance"""
        logger.info("\n" + "="*60)
        logger.info("GITLAB AUTHENTICATION REQUIRED")
        logger.info("="*60)
        logger.info(f"GitLab URL: {self.gitlab_url}")
        logger.info(f"Current browser URL: {self.driver.current_url}")
        logger.info("\nInstructions:")
        logger.info("1. The browser window should now be open showing your GitLab login page")
        logger.info("2. Complete the sign-in process (including any SSO/corporate authentication)")
        logger.info("3. Wait until you can see your GitLab dashboard")
        logger.info("4. DO NOT CLOSE THE BROWSER - it will be used for processing")
        logger.info("5. Return here and press Enter when sign-in is complete")
        logger.info("="*60)
        
        max_attempts = 3
        attempt = 1
        
        while attempt <= max_attempts:
            logger.info(f"\nSign-in attempt {attempt}/{max_attempts}")
            input("Press Enter after completing GitLab sign-in...")
            
            try:
                # Refresh and check authentication
                logger.info("Verifying sign-in status...")
                self.driver.refresh()
                
                # Wait for page load
                WebDriverWait(self.driver, VERIFICATION_TIMEOUT).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                time.sleep(3)
                
                # Check if still on login page
                if self._detect_login_page():
                    logger.warning(f"Still on login page. Please complete sign-in process.")
                    if attempt < max_attempts:
                        logger.info("Please try again...")
                        attempt += 1
                        continue
                    else:
                        logger.error("Failed to complete sign-in after multiple attempts")
                        raise Exception("GitLab authentication failed")
                
                # Verify authentication
                if self._verify_authenticated_session():
                    logger.info("✓ GitLab sign-in verified successfully!")
                    self.browser_session_available = True
                    break
                else:
                    logger.warning("Sign-in verification inconclusive")
                    if attempt < max_attempts:
                        response = input("Continue anyway? Authentication may still work. (y/n): ").lower().strip()
                        if response == 'y':
                            logger.info("Continuing with unverified browser session...")
                            self.browser_session_available = True
                            break
                        else:
                            attempt += 1
                            continue
                    else:
                        # Last attempt - give user choice
                        response = input("Final attempt: Continue with current session? (y/n): ").lower().strip()
                        if response == 'y':
                            logger.info("Continuing with unverified browser session...")
                            self.browser_session_available = True
                            break
                        else:
                            raise Exception("GitLab browser authentication required but not completed")
                            
            except Exception as e:
                logger.error(f"Error during sign-in verification: {e}")
                if attempt < max_attempts:
                    attempt += 1
                    continue
                else:
                    raise

    def verify_browser_session_strict(self):
        """Strict browser session verification when API is not available"""
        logger.warning("API access is not available. Browser session is required for operation.")
        self.verify_browser_session_enhanced()
        
        if not self.browser_session_available:
            raise Exception("Browser session is required but could not be established")

    def check_mr_accessibility(self, project_id: str, mr_iid: str) -> Dict:
        """
        Enhanced MR accessibility check with better error handling
        """
        result = {
            'accessible': False,
            'api_accessible': False,
            'browser_accessible': False,
            'mr_info': None,
            'error': None
        }

        try:
            # API access check
            if self.api_access_working:
                logger.info(f"Checking API access for MR {project_id}/{mr_iid}")
                mr_info = self.get_merge_request_info(project_id, mr_iid)

                if mr_info:
                    result['api_accessible'] = True
                    result['mr_info'] = mr_info
                    logger.info(f"✓ API access successful for MR {project_id}/{mr_iid}: {mr_info.get('title', 'No title')}")
                else:
                    logger.warning(f"✗ API access failed for MR {project_id}/{mr_iid}")

            # Browser access check
            if self.browser_session_available and (not result['api_accessible'] or not self.skip_browser):
                logger.info(f"Checking browser access for MR {project_id}/{mr_iid}")
                browser_accessible = self.check_mr_browser_access(project_id, mr_iid, result)
                
                if browser_accessible and not result['mr_info']:
                    # Try to extract basic info from browser
                    self.extract_mr_info_from_browser(project_id, mr_iid, result)

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

    def check_mr_browser_access(self, project_id: str, mr_iid: str, result: Dict) -> bool:
        """Check MR access via browser"""
        try:
            mr_url = f"{self.gitlab_url}/{project_id}/-/merge_requests/{mr_iid}"
            
            # Switch to GitLab tab
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.get(mr_url)
            
            # Wait for page load
            WebDriverWait(self.driver, VERIFICATION_TIMEOUT).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(3)

            # Check for access denied or not found
            error_indicators = [
                ".access-denied", ".not-found", ".error-message", 
                ".permission-denied", ".page-404", ".error-content"
            ]
            
            for selector in error_indicators:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
                    result['error'] = f"Access denied or MR not found via browser (selector: {selector})"
                    return False

            # Check for error text
            error_texts = ["404", "not found", "access denied", "permission", "unauthorized"]
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            for error_text in error_texts:
                if error_text in page_text and "merge request" not in page_text:
                    result['error'] = f"Error page detected: {error_text}"
                    return False

            # Look for MR content
            mr_indicators = [
                ".merge-request", ".mr-widget", ".mr-state-widget", 
                ".issuable-meta", ".merge-request-details", ".mr-tabs"
            ]
            
            for selector in mr_indicators:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
                    result['browser_accessible'] = True
                    logger.info(f"✓ Browser access successful for MR {project_id}/{mr_iid}")
                    return True

            # Fallback: check for merge request specific text
            if "merge request" in page_text or "merge_request" in page_text:
                result['browser_accessible'] = True
                logger.info(f"✓ Browser access successful for MR {project_id}/{mr_iid} (text-based detection)")
                return True

            result['error'] = "MR content not found in browser"
            return False

        except Exception as e:
            result['error'] = f"Browser access check failed: {str(e)}"
            logger.warning(f"Error checking browser access: {e}")
            return False

    def extract_mr_info_from_browser(self, project_id: str, mr_iid: str, result: Dict):
        """Extract MR information from browser when API is not available"""
        try:
            mr_url = f"{self.gitlab_url}/{project_id}/-/merge_requests/{mr_iid}"
            
            # Extract title
            title_selectors = [
                ".issue-title", ".merge-request-title", 
                "h1.title", ".title", ".issuable-header-text h1"
            ]
            
            title = "Unknown Title"
            for selector in title_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    title = elements[0].text.strip()
                    break

            result['mr_info'] = {
                'title': title,
                'web_url': mr_url,
                'iid': mr_iid,
                'source': 'browser'
            }
            
            logger.info(f"Extracted MR title from browser: {title}")

        except Exception as e:
            logger.warning(f"Could not extract MR info from browser: {e}")

    def setup_chrome_driver(self):
        """Setup Chrome WebDriver with enhanced options for corporate environments"""
        chrome_options = Options()
        
        # Corporate environment options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        
        # Persistent session for authentication
        chrome_options.add_argument('--user-data-dir=/tmp/chrome_profile_gitlab')
        
        # Remove automation indicators
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Enable verbose logging for debugging
        chrome_options.add_argument('--enable-logging')
        chrome_options.add_argument('--v=1')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.maximize_window()
            
            # Set longer timeouts for corporate networks
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            logger.error("Please ensure ChromeDriver is installed and in PATH")
            raise

    def get_merge_request_info(self, project_id: str, mr_iid: str) -> Dict:
        """Enhanced MR info retrieval with better error handling"""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
            
            # Use SSL verification setting if configured
            verify_ssl = getattr(self, 'ssl_verify', True)
            response = requests.get(url, headers=self.headers, timeout=30, verify=verify_ssl)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.error(f"MR {project_id}/{mr_iid} not found")
                return None
            elif response.status_code == 403:
                logger.error(f"Access denied to MR {project_id}/{mr_iid}")
                return None
            else:
                logger.error(f"Failed to get MR info: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.SSLError:
            logger.warning("SSL error, retrying without verification...")
            try:
                response = requests.get(url, headers=self.headers, timeout=30, verify=False)
                if response.status_code == 200:
                    self.ssl_verify = False  # Remember for future requests
                    return response.json()
            except Exception as e:
                logger.error(f"Failed even without SSL verification: {e}")
                
        except Exception as e:
            logger.error(f"Error getting MR info: {e}")
            
        return None

    def setup_gemini_web_interface(self):
        """Setup Gemini web interface with better error handling"""
        try:
            logger.info("Opening Gemini web interface...")
            self.driver.execute_script("window.open('https://gemini.google.com/', '_blank');")

            # Switch to the new Gemini tab
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # Wait for page to load
            time.sleep(5)

            # Check if we need to sign in
            try:
                # Look for the text input area with longer timeout
                WebDriverWait(self.driver, 20).until(
                    lambda driver: driver.find_element(By.CSS_SELECTOR, "[data-test-id='input-area']") or
                                   driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true']") or
                                   driver.find_element(By.TAG_NAME, "textarea")
                )
                logger.info("✓ Gemini interface is ready")

            except Exception as e:
                logger.warning("Gemini interface might require manual sign-in.")
                logger.info("Please sign in to Gemini manually in the browser window.")
                input("Press Enter after signing in to Gemini...")

            # Switch back to GitLab tab
            self.driver.switch_to.window(self.driver.window_handles[0])

        except Exception as e:
            logger.error(f"Error setting up Gemini interface: {e}")
            logger.warning("Continuing without Gemini - documentation will use fallback method")

    def generate_documentation_for_mr(self, project_id: str, mr_iid: str) -> str:
        """Generate documentation for a single MR"""
        try:
            # Check MR accessibility first  
            accessibility = self.check_mr_accessibility(project_id, mr_iid)
            
            if not accessibility['accessible']:
                return f"Error: {accessibility.get('error', 'MR not accessible')}"
            
            mr_info = accessibility['mr_info']
            
            # Get changes if API is available
            java_changes = []
            if self.api_access_working:
                changes_data = self.get_merge_request_changes(project_id, mr_iid)
                if changes_data:
                    java_changes = self.extract_java_changes(changes_data)
            
            # Generate documentation using Gemini or fallback
            if hasattr(self, 'driver') and len(self.driver.window_handles) > 1:
                try:
                    documentation = self.analyze_code_changes_with_gemini(java_changes, mr_info)
                    if documentation and not documentation.startswith("Error"):
                        return documentation
                except Exception as e:
                    logger.warning(f"Gemini analysis failed: {e}")
            
            # Fallback documentation generation
            return self.generate_fallback_documentation(mr_info, java_changes)
            
        except Exception as e:
            logger.error(f"Error generating documentation for MR {project_id}/{mr_iid}: {e}")
            return f"Error generating documentation: {str(e)}"

    def generate_fallback_documentation(self, mr_info: Dict, java_changes: List[Dict]) -> str:
        """Generate basic documentation when Gemini is not available"""
        doc = f"""# Merge Request Documentation

## Summary
**Title:** {mr_info.get('title', 'N/A')}  
**Author:** {mr_info.get('author', {}).get('name', 'N/A')}  
**Source Branch:** {mr_info.get('source_branch', 'N/A')}  
**Target Branch:** {mr_info.get('target_branch', 'N/A')}  
**Created:** {mr_info.get('created_at', 'N/A')}  
**URL:** {mr_info.get('web_url', 'N/A')}

## Description
{mr_info.get('description', 'No description provided')}

## Technical Changes
"""
        
        if java_changes:
            doc += f"**Java Files Modified:** {len(java_changes)}\n\n"
            for i, change in enumerate(java_changes[:10], 1):  # Limit to 10 files
                status = "New" if change['new_file'] else "Modified" if not change['deleted_file'] else "Deleted"
                doc += f"{i}. **{change['file_path']}** - {status}\n"
            
            if len(java_changes) > 10:
                doc += f"\n... and {len(java_changes) - 10} more Java files\n"
        else:
            doc += "No Java file changes detected or changes could not be retrieved.\n"

        doc += """
## Notes
- This documentation was generated automatically
- For detailed code analysis, manual review is recommended
- Gemini AI analysis was not available for this merge request
"""
        
        return doc

    def get_merge_request_changes(self, project_id: str, mr_iid: str) -> Dict:
        """Get merge request changes with enhanced error handling"""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
            verify_ssl = getattr(self, 'ssl_verify', True)
            response = requests.get(url, headers=self.headers, timeout=30, verify=verify_ssl)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get MR changes: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting MR changes: {e}")
            return None

    def extract_java_changes(self, changes_data: Dict) -> List[Dict]:
        """Extract Java file changes from the changes data"""
        java_changes = []

        if 'changes' in changes_data:
            for change in changes_data['changes']:
                if change.get('old_path', '').endswith('.java') or change.get('new_path', '').endswith('.java'):
                    java_changes.append({
                        'file_path': change.get('new_path') or change.get('old_path'),
                        'old_path': change.get('old_path'),
                        'new_path': change.get('new_path'),
                        'new_file': change.get('new_file', False),
                        'renamed_file': change.get('renamed_file', False),
                        'deleted_file': change.get('deleted_file', False),
                        'diff': change.get('diff', '')
                    })

        return java_changes

    def analyze_code_changes_with_gemini(self, java_changes: List[Dict], mr_info: Dict) -> str:
        """Analyze code changes using Gemini AI"""
        try:
            if not java_changes:
                return self.generate_fallback_documentation(mr_info, java_changes)

            # Switch to Gemini tab
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # Prepare the prompt for Gemini
            prompt = self.create_gemini_prompt(java_changes, mr_info)

            # Find the input area
            input_selectors = [
                "[data-test-id='input-area']",
                "div[contenteditable='true']",
                "textarea",
                ".chat-input",
                ".input-area"
            ]

            input_element = None
            for selector in input_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    input_element = elements[0]
                    break

            if not input_element:
                logger.warning("Could not find Gemini input area")
                return self.generate_fallback_documentation(mr_info, java_changes)

            # Clear any existing text and input the prompt
            input_element.clear()
            time.sleep(1)

            # Type the prompt in chunks to avoid issues with long text
            self.type_text_in_chunks(input_element, prompt)

            # Send the message
            self.send_gemini_message()

            # Wait for and get the response
            response = self.get_gemini_response()

            # Switch back to GitLab tab
            self.driver.switch_to.window(self.driver.window_handles[0])

            return response if response else self.generate_fallback_documentation(mr_info, java_changes)

        except Exception as e:
            logger.error(f"Error analyzing with Gemini: {e}")
            # Switch back to GitLab tab if error occurs
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return self.generate_fallback_documentation(mr_info, java_changes)

    def create_gemini_prompt(self, java_changes: List[Dict], mr_info: Dict) -> str:
        """Create a comprehensive prompt for Gemini analysis"""
        prompt = f"""Analyze this GitLab merge request and provide comprehensive technical documentation:

**Merge Request Details:**
- Title: {mr_info.get('title', 'N/A')}
- Author: {mr_info.get('author', {}).get('name', 'N/A')}
- Description: {mr_info.get('description', 'No description provided')}
- Source Branch: {mr_info.get('source_branch', 'N/A')}
- Target Branch: {mr_info.get('target_branch', 'N/A')}

**Java Files Changed ({len(java_changes)} files):**
"""

        # Add file-by-file analysis with diffs
        for i, change in enumerate(java_changes[:5], 1):  # Limit to 5 files to avoid token limits
            status = "New" if change['new_file'] else "Modified" if not change['deleted_file'] else "Deleted"
            prompt += f"\n{i}. **{change['file_path']}** ({status})\n"

            if change['diff'] and len(change['diff']) < 3000:  # Limit diff size
                prompt += f"```diff\n{change['diff'][:3000]}\n```\n"
            elif change['diff']:
                prompt += f"```diff\n{change['diff'][:1500]}...\n[Diff truncated for brevity]\n```\n"

        if len(java_changes) > 5:
            prompt += f"\n... and {len(java_changes) - 5} more Java files modified\n"

        prompt += """
Please provide a comprehensive analysis including:

1. **Executive Summary** - Brief overview of what this MR accomplishes
2. **Technical Changes** - Detailed breakdown of code modifications
3. **Architecture Impact** - How these changes affect the overall system
4. **Key Features/Improvements** - New functionality or enhancements
5. **Potential Risks** - Any concerns or areas that need attention
6. **Testing Recommendations** - Suggested test scenarios
7. **Deployment Notes** - Any special considerations for deployment

Format the response in clean Markdown with proper headings and bullet points.
"""

        return prompt

    def type_text_in_chunks(self, element, text: str, chunk_size: int = 500):
        """Type text in chunks to avoid overwhelming the input"""
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            element.send_keys(chunk)
            time.sleep(0.5)  # Small delay between chunks

    def send_gemini_message(self):
        """Send the message in Gemini"""
        try:
            # Try different methods to send the message
            send_selectors = [
                "[data-test-id='send-button']",
                "button[type='submit']",
                ".send-button",
                "button[aria-label='Send']"
            ]

            for selector in send_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    elements[0].click()
                    return

            # Fallback: try Enter key
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()

        except Exception as e:
            logger.warning(f"Error sending Gemini message: {e}")
            # Try simple Enter as last resort
            ActionChains(self.driver).send_keys(Keys.RETURN).perform()

    def get_gemini_response(self, timeout: int = 120) -> str:
        """Wait for and extract Gemini's response"""
        try:
            logger.info("Waiting for Gemini response...")

            # Wait for response to appear
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Look for response elements
                response_selectors = [
                    "[data-test-id='response']",
                    ".response-content",
                    ".message-content",
                    ".chat-message",
                    "[role='presentation']"
                ]

                for selector in response_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Get the last (most recent) response
                        response_element = elements[-1]
                        response_text = response_element.text.strip()

                        # Check if response is complete (not just loading)
                        if len(response_text) > 100 and not response_text.endswith("..."):
                            logger.info("✓ Gemini response received")
                            return response_text

                time.sleep(2)  # Check every 2 seconds

            logger.warning("Timeout waiting for Gemini response")
            return ""

        except Exception as e:
            logger.error(f"Error getting Gemini response: {e}")
            return ""

    def generate_documentation(self, output_filename: str = None) -> str:
        """Generate documentation for all configured merge requests"""
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"mr_documentation_{timestamp}.md"

        logger.info(f"Starting documentation generation for {len(MERGE_REQUESTS)} merge requests...")

        all_documentation = []
        all_documentation.append("# GitLab Merge Request Documentation Report")
        all_documentation.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        all_documentation.append(f"GitLab Instance: {self.gitlab_url}")
        all_documentation.append("\n---\n")

        successful_mrs = 0
        failed_mrs = 0

        for i, mr in enumerate(MERGE_REQUESTS, 1):
            project_id = mr['project_id']
            mr_iid = mr['mr_iid']

            logger.info(f"Processing MR {i}/{len(MERGE_REQUESTS)}: {project_id}/{mr_iid}")

            try:
                doc = self.generate_documentation_for_mr(project_id, mr_iid)

                if doc.startswith("Error"):
                    logger.error(f"Failed to process MR {project_id}/{mr_iid}: {doc}")
                    all_documentation.append(f"## MR {project_id}/{mr_iid} - FAILED")
                    all_documentation.append(f"**Error:** {doc}")
                    failed_mrs += 1
                else:
                    all_documentation.append(doc)
                    successful_mrs += 1
                    logger.info(f"✓ Successfully processed MR {project_id}/{mr_iid}")

                all_documentation.append("\n---\n")

                # Small delay between MRs to avoid rate limiting
                time.sleep(2)

            except Exception as e:
                logger.error(f"Unexpected error processing MR {project_id}/{mr_iid}: {e}")
                all_documentation.append(f"## MR {project_id}/{mr_iid} - ERROR")
                all_documentation.append(f"**Unexpected Error:** {str(e)}")
                all_documentation.append("\n---\n")
                failed_mrs += 1

        # Add summary
        summary = f"""
## Generation Summary
- **Total MRs Processed:** {len(MERGE_REQUESTS)}
- **Successful:** {successful_mrs}
- **Failed:** {failed_mrs}
- **Success Rate:** {(successful_mrs / len(MERGE_REQUESTS) * 100):.1f}%
"""
        all_documentation.insert(4, summary)

        # Write to file
        final_content = "\n".join(all_documentation)

        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(final_content)

            logger.info(f"✓ Documentation saved to: {output_filename}")
            logger.info(f"Summary: {successful_mrs}/{len(MERGE_REQUESTS)} MRs processed successfully")

        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
            # Fallback: print to console
            print("=" * 80)
            print("DOCUMENTATION OUTPUT (could not save to file):")
            print("=" * 80)
            print(final_content)
            print("=" * 80)

        return output_filename

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
            logger.info("✓ Resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


def main():
    """Main execution function"""
    try:
        logger.info("=" * 60)
        logger.info("GITLAB MERGE REQUEST DOCUMENTATION GENERATOR")
        logger.info("=" * 60)

        # Validate configuration
        if not GITLAB_URL or not PRIVATE_TOKEN:
            logger.error("Please configure GITLAB_URL and PRIVATE_TOKEN in the script")
            return

        if not MERGE_REQUESTS:
            logger.error("Please configure MERGE_REQUESTS list in the script")
            return

        # Initialize the generator
        generator = GitLabMRDocumentationGenerator(GITLAB_URL, PRIVATE_TOKEN)

        # Generate documentation
        output_file = generator.generate_documentation(OUTPUT_FILENAME)

        logger.info("=" * 60)
        logger.info("DOCUMENTATION GENERATION COMPLETE")
        logger.info(f"Output file: {output_file}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Cleanup
        try:
            if 'generator' in locals():
                generator.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()