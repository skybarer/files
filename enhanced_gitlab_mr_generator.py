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
import re

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gitlab_mr_generator.log'),
        logging.StreamHandler()
    ]
)
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

# Enhanced file type detection
SUPPORTED_FILE_EXTENSIONS = {
    'java': ['.java'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx'],
    'react': ['.jsx', '.tsx'],
    'spring': ['.java'],  # Will be filtered by Spring-specific patterns
    'frontend': ['.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass'],
    'config': ['.json', '.yml', '.yaml', '.xml', '.properties'],
    'test': ['.test.js', '.spec.js', '.test.java', '.spec.java']
}

# Spring Boot specific patterns
SPRING_BOOT_PATTERNS = [
    r'@SpringBootApplication',
    r'@RestController',
    r'@Controller',
    r'@Service',
    r'@Repository',
    r'@Component',
    r'@Configuration',
    r'@Entity',
    r'@RequestMapping',
    r'@GetMapping',
    r'@PostMapping',
    r'@PutMapping',
    r'@DeleteMapping',
    r'@Autowired',
    r'@Value',
    r'@ConfigurationProperties',
    r'org\.springframework',
    r'spring-boot'
]

# React specific patterns
REACT_PATTERNS = [
    r'import.*React',
    r'from\s+[\'"]react[\'"]',
    r'useState',
    r'useEffect',
    r'useContext',
    r'useReducer',
    r'React\.Component',
    r'ReactDOM',
    r'JSX\.Element',
    r'export.*default.*function',
    r'const.*=.*\(\)\s*=>'
]

# ========================================
# END CONFIGURATION SECTION
# ========================================


class GitLabMRDocumentationGenerator:
    def __init__(self, gitlab_url: str, private_token: str):
        """
        Initialize the documentation generator with enhanced file type support

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
        self.gemini_ready = False

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
        """Setup Gemini web interface with enhanced logging"""
        try:
            logger.info("🚀 Setting up Gemini web interface...")
            
            # Check if we already have tabs open
            initial_tabs = len(self.driver.window_handles)
            logger.info(f"Current number of browser tabs: {initial_tabs}")
            
            # Open Gemini in a new tab
            logger.info("Opening Gemini in new tab...")
            self.driver.execute_script("window.open('https://gemini.google.com/', '_blank');")
            
            # Wait for tab to open
            time.sleep(3)
            new_tabs = len(self.driver.window_handles)
            logger.info(f"New number of browser tabs: {new_tabs}")
            
            if new_tabs <= initial_tabs:
                logger.warning("New tab may not have opened properly")
                return False

            # Switch to the new Gemini tab
            logger.info("Switching to Gemini tab...")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            current_url = self.driver.current_url
            logger.info(f"Current URL in Gemini tab: {current_url}")

            # Wait for page to load
            logger.info("Waiting for Gemini page to load...")
            time.sleep(8)  # Increased wait time

            # Check if we're on the right page
            current_url = self.driver.current_url
            logger.info(f"Gemini page loaded. Current URL: {current_url}")
            
            if "gemini.google.com" not in current_url:
                logger.warning(f"May not be on Gemini page. Current URL: {current_url}")

            # Check for sign-in requirement
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            logger.info(f"Page text length: {len(page_text)} characters")
            
            if "sign in" in page_text or "sign up" in page_text:
                logger.warning("⚠️  Gemini appears to require sign-in")
                logger.info("Please sign in to Gemini manually in the browser window.")
                logger.info("The script will wait for you to complete sign-in...")
                input("Press Enter after signing in to Gemini...")
                
                # Refresh and check again
                self.driver.refresh()
                time.sleep(5)
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()

            # Look for the input area with multiple strategies
            logger.info("🔍 Looking for Gemini input area...")
            input_found = False
            
            input_selectors = [
                "[data-test-id='input-area']",
                "div[contenteditable='true']",
                "textarea",
                ".chat-input",
                ".input-area",
                "[role='textbox']",
                ".ProseMirror",
                "[data-testid='input-area']"
            ]

            for i, selector in enumerate(input_selectors):
                logger.info(f"Trying selector {i+1}/{len(input_selectors)}: {selector}")
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"✅ Found {len(elements)} elements with selector: {selector}")
                    # Try to click on the first element to see if it activates
                    try:
                        elements[0].click()
                        time.sleep(1)
                        logger.info(f"✅ Successfully clicked on input element")
                        input_found = True
                        break
                    except Exception as e:
                        logger.warning(f"Could not click on element: {e}")
                else:
                    logger.info(f"❌ No elements found with selector: {selector}")

            if input_found:
                logger.info("✅ Gemini interface appears to be ready!")
                self.gemini_ready = True
            else:
                logger.warning("⚠️  Could not