# WebDriver Troubleshooting Guide for Corporate Environments

## Common Issues and Solutions

### 1. ChromeDriver Installation and Path Issues
```bash
# Install ChromeDriver using package manager (recommended)
pip install webdriver-manager

# Or download manually from:
# https://chromedriver.chromium.org/downloads
```

### 2. Corporate Proxy/Firewall Issues
```python
# Add proxy settings to Chrome options
chrome_options.add_argument('--proxy-server=http://your-proxy:port')
chrome_options.add_argument('--proxy-bypass-list=localhost,127.0.0.1')
```

### 3. Corporate Security Policies
```python
# Disable security features that might be blocked
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--disable-features=VizDisplayCompositor')
chrome_options.add_argument('--disable-extensions')
```

## Fixed GitLab MR Documentation Generator

import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time
import os
import sys
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitLabMRDocumentationGenerator:
    def __init__(self, gitlab_url: str, private_token: str, use_headless: bool = False):
        """
        Initialize the documentation generator with improved error handling
        
        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.example.com)
            private_token: GitLab private access token
            use_headless: Whether to run Chrome in headless mode
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.private_token = private_token
        self.headers = {'PRIVATE-TOKEN': private_token}
        self.driver = None
        self.use_headless = use_headless
        
        # Setup Chrome driver with error handling
        if not self.setup_chrome_driver():
            logger.error("Failed to setup Chrome driver. Exiting...")
            sys.exit(1)
    
    def setup_chrome_driver(self) -> bool:
        """Setup Chrome WebDriver with improved options for corporate environments"""
        try:
            chrome_options = Options()
            
            # Corporate environment friendly options
            if self.use_headless:
                chrome_options.add_argument('--headless')
            
            # Essential options for corporate networks
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Faster loading
            chrome_options.add_argument('--disable-javascript')  # For faster loading (remove if JS needed)
            
            # Bypass corporate security features
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # User agent to avoid detection
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Proxy settings (uncomment and modify if needed)
            # chrome_options.add_argument('--proxy-server=http://your-proxy:port')
            # chrome_options.add_argument('--proxy-bypass-list=localhost,127.0.0.1')
            
            # Certificate issues (common in corporate environments)
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--ignore-certificate-errors-spki-list')
            
            # Window size
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Disable automation flags
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Use temporary profile
            chrome_options.add_argument('--user-data-dir=/tmp/chrome_temp_profile')
            
            # Try to use ChromeDriverManager for automatic driver management
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome driver initialized successfully with ChromeDriverManager")
            except Exception as e:
                logger.warning(f"ChromeDriverManager failed: {e}")
                logger.info("Trying to use system ChromeDriver...")
                
                # Fallback to system ChromeDriver
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    logger.info("Chrome driver initialized successfully with system ChromeDriver")
                except Exception as e2:
                    logger.error(f"System ChromeDriver also failed: {e2}")
                    return False
            
            # Set script timeout
            self.driver.set_script_timeout(60)
            self.driver.set_page_load_timeout(60)
            
            # Prevent webdriver detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Test the driver
            try:
                self.driver.get("https://www.google.com")
                logger.info("Chrome driver test successful")
                return True
            except Exception as e:
                logger.error(f"Chrome driver test failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}")
            return False
    
    def test_gitlab_connection(self) -> bool:
        """Test GitLab API connection"""
        try:
            url = f"{self.gitlab_url}/api/v4/user"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"GitLab connection successful. User: {user_info.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"GitLab connection failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"GitLab connection error: {e}")
            return False
    
    def setup_gemini_web_interface(self) -> bool:
        """Setup Gemini web interface with better error handling"""
        try:
            logger.info("Opening Gemini web interface...")
            self.driver.get("https://gemini.google.com/")
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Check if we need to sign in
            try:
                # Look for various input selectors
                input_selectors = [
                    "[data-test-id='input-area']",
                    "div[contenteditable='true']",
                    "textarea",
                    ".ql-editor",
                    "[role='textbox']",
                    "div[aria-label*='Message']",
                    "div[placeholder*='Enter a prompt']"
                ]
                
                input_found = False
                for selector in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if element:
                            logger.info(f"Found Gemini input with selector: {selector}")
                            input_found = True
                            break
                    except:
                        continue
                
                if input_found:
                    logger.info("Gemini interface is ready")
                    return True
                else:
                    logger.warning("Gemini interface might require manual sign-in")
                    print("Please sign in to Gemini manually in the browser window")
                    input("Press Enter after signing in to continue...")
                    return True
                    
            except Exception as e:
                logger.error(f"Error checking Gemini interface: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up Gemini interface: {e}")
            return False
    
    def get_merge_request_info(self, project_id: str, mr_iid: str) -> Optional[Dict]:
        """Get merge request information from GitLab API with error handling"""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get MR info for {project_id}/{mr_iid}: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting MR info: {e}")
            return None
    
    def get_merge_request_changes(self, project_id: str, mr_iid: str) -> Optional[Dict]:
        """Get merge request changes from GitLab API with error handling"""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get MR changes for {project_id}/{mr_iid}: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting MR changes: {e}")
            return None
    
    def extract_java_changes(self, changes_data: Dict) -> List[Dict]:
        """Extract Java file changes from the changes data"""
        java_changes = []
        
        try:
            if 'changes' in changes_data:
                for change in changes_data['changes']:
                    if change.get('new_path', '').endswith('.java'):
                        java_changes.append({
                            'file_path': change.get('new_path', ''),
                            'old_path': change.get('old_path', change.get('new_path', '')),
                            'diff': change.get('diff', ''),
                            'new_file': change.get('new_file', False),
                            'deleted_file': change.get('deleted_file', False),
                            'renamed_file': change.get('renamed_file', False)
                        })
        except Exception as e:
            logger.error(f"Error extracting Java changes: {e}")
            
        return java_changes
    
    def generate_documentation_simple(self, java_changes: List[Dict], mr_info: Dict) -> str:
        """
        Generate simple documentation without Gemini (fallback method)
        """
        doc = f"""# Merge Request Documentation

## Basic Information
- **Title**: {mr_info.get('title', 'N/A')}
- **Author**: {mr_info.get('author', {}).get('name', 'N/A')}
- **Source Branch**: {mr_info.get('source_branch', 'N/A')}
- **Target Branch**: {mr_info.get('target_branch', 'N/A')}
- **Created**: {mr_info.get('created_at', 'N/A')}
- **Description**: {mr_info.get('description', 'N/A')}

## Files Changed
Total Java files modified: {len(java_changes)}

"""
        
        for i, change in enumerate(java_changes, 1):
            status = "New" if change['new_file'] else "Modified" if not change['deleted_file'] else "Deleted"
            if change['renamed_file']:
                status += " (Renamed)"
                
            doc += f"""
### {i}. {change['file_path']}
- **Status**: {status}
- **Lines Changed**: {len(change['diff'].split('\n')) if change['diff'] else 0}

"""
        
        return doc
    
    def generate_documentation_for_mr(self, project_id: str, mr_iid: str, use_simple: bool = False) -> str:
        """
        Generate documentation for a single merge request
        
        Args:
            project_id: GitLab project ID
            mr_iid: Merge request internal ID
            use_simple: Use simple documentation generation (no Gemini)
            
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
        
        # Generate documentation
        if use_simple:
            documentation = self.generate_documentation_simple(java_changes, mr_info)
        else:
            # Try to use Gemini (implement your Gemini logic here)
            documentation = self.generate_documentation_simple(java_changes, mr_info)
            
        return documentation
    
    def save_documentation_to_file(self, documentation: str, filename: str):
        """Save documentation to a file"""
        try:
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(documentation)
            logger.info(f"Documentation saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Chrome driver: {e}")

# Simplified main function for testing
def main():
    # Configuration - REPLACE WITH YOUR VALUES
    GITLAB_URL = "https://your-gitlab-instance.com"
    GITLAB_TOKEN = "your-private-token-here"
    
    # Test with a single MR first
    TEST_PROJECT_ID = "123"
    TEST_MR_IID = "45"
    
    print("Starting GitLab MR Documentation Generator...")
    print("This version includes WebDriver fixes for corporate environments")
    
    # Initialize the generator
    try:
        doc_generator = GitLabMRDocumentationGenerator(
            gitlab_url=GITLAB_URL,
            private_token=GITLAB_TOKEN,
            use_headless=True  # Set to False if you want to see the browser
        )
        
        # Test GitLab connection first
        if not doc_generator.test_gitlab_connection():
            print("GitLab connection failed. Please check your URL and token.")
            return
        
        # Generate documentation for a single MR (simple version)
        documentation = doc_generator.generate_documentation_for_mr(
            TEST_PROJECT_ID, 
            TEST_MR_IID, 
            use_simple=True
        )
        
        # Save the documentation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"MR_Documentation_{TEST_PROJECT_ID}_{TEST_MR_IID}_{timestamp}.md"
        doc_generator.save_documentation_to_file(documentation, filename)
        
        print(f"Documentation generated successfully!")
        print(f"File saved as: {filename}")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Main execution error: {e}")
        
    finally:
        if 'doc_generator' in locals():
            doc_generator.cleanup()

if __name__ == "__main__":
    main()
