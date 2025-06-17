# ========================================
# CONFIGURATION SECTION - ADD THESE NEW OPTIONS
# ========================================

# Chrome Profile Configuration
USE_EXISTING_PROFILE = True  # Set to True to use existing Chrome profile
CHROME_PROFILE_PATH = ""  # Leave empty for default profile, or specify custom path
CHROME_PROFILE_NAME = "Default"  # Profile name (usually "Default" or "Profile 1", "Profile 2", etc.)

# Alternative: Use specific user data directory
# CHROME_USER_DATA_DIR = "/path/to/your/chrome/user/data"  # Uncomment and set if needed

# ========================================
# UPDATED METHOD - Replace the existing setup_chrome_driver method
# ========================================

def setup_chrome_driver(self):
    """Setup Chrome WebDriver with existing profile support"""
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
    
    # Profile Configuration
    if USE_EXISTING_PROFILE:
        if CHROME_PROFILE_PATH:
            # Use custom profile path
            logger.info(f"Using custom Chrome profile path: {CHROME_PROFILE_PATH}")
            chrome_options.add_argument(f'--user-data-dir={CHROME_PROFILE_PATH}')
        else:
            # Use default Chrome profile location
            user_data_dir = self.get_default_chrome_profile_path()
            if user_data_dir:
                logger.info(f"Using default Chrome profile: {user_data_dir}")
                chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
                
                # Specify profile name if not default
                if CHROME_PROFILE_NAME and CHROME_PROFILE_NAME != "Default":
                    chrome_options.add_argument(f'--profile-directory={CHROME_PROFILE_NAME}')
                    logger.info(f"Using profile: {CHROME_PROFILE_NAME}")
            else:
                logger.warning("Could not find default Chrome profile, using temporary profile")
                chrome_options.add_argument('--user-data-dir=/tmp/chrome_profile_gitlab')
    else:
        # Use temporary profile (original behavior)
        chrome_options.add_argument('--user-data-dir=/tmp/chrome_profile_gitlab')
    
    # Remove automation indicators
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Enable verbose logging for debugging
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--v=1')
    
    # Disable password save prompts and other notifications
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)

    try:
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.maximize_window()
        
        # Set longer timeouts for corporate networks
        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(10)
        
        logger.info("✅ Chrome driver setup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {e}")
        logger.error("Please ensure ChromeDriver is installed and in PATH")
        raise

def get_default_chrome_profile_path(self):
    """Get the default Chrome profile path for the current OS"""
    import platform
    import os
    from pathlib import Path
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows Chrome profile path
            user_data_dir = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
        elif system == "Darwin":  # macOS
            # macOS Chrome profile path
            user_data_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
        elif system == "Linux":
            # Linux Chrome profile path
            user_data_dir = os.path.expanduser('~/.config/google-chrome')
        else:
            logger.warning(f"Unsupported operating system: {system}")
            return None
        
        # Check if the directory exists
        if os.path.exists(user_data_dir):
            logger.info(f"Found Chrome user data directory: {user_data_dir}")
            return user_data_dir
        else:
            logger.warning(f"Chrome user data directory not found: {user_data_dir}")
            return None
            
    except Exception as e:
        logger.error(f"Error finding Chrome profile path: {e}")
        return None

# ========================================
# HELPER METHOD TO LIST AVAILABLE PROFILES
# ========================================

def list_chrome_profiles(self):
    """List available Chrome profiles for user selection"""
    user_data_dir = self.get_default_chrome_profile_path()
    
    if not user_data_dir or not os.path.exists(user_data_dir):
        logger.warning("Cannot find Chrome user data directory")
        return []
    
    profiles = []
    
    try:
        # Look for profile directories
        for item in os.listdir(user_data_dir):
            item_path = os.path.join(user_data_dir, item)
            
            if os.path.isdir(item_path):
                # Check if it's a profile directory
                if item == "Default" or item.startswith("Profile "):
                    profiles.append(item)
        
        logger.info(f"Found Chrome profiles: {profiles}")
        return profiles
        
    except Exception as e:
        logger.error(f"Error listing Chrome profiles: {e}")
        return []

# ========================================
# ADDITIONAL CONFIGURATION OPTIONS
# ========================================

# Add these to the main configuration section if you want more control:

# Chrome Browser Options
CHROME_HEADLESS = False  # Set to True to run Chrome in headless mode
CHROME_WINDOW_SIZE = "1920,1080"  # Browser window size
CHROME_DISABLE_EXTENSIONS = False  # Set to True to disable all extensions

# Enhanced Chrome Options (add to setup_chrome_driver method if needed)
def setup_enhanced_chrome_options(self):
    """Additional Chrome options for better compatibility"""
    chrome_options = Options()
    
    # ... existing options ...
    
    # Additional options for better profile support
    if CHROME_HEADLESS:
        chrome_options.add_argument('--headless=new')  # Use new headless mode
    
    chrome_options.add_argument(f'--window-size={CHROME_WINDOW_SIZE}')
    
    if CHROME_DISABLE_EXTENSIONS:
        chrome_options.add_argument('--disable-extensions')
    
    # Better session persistence
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-dev-tools')
    
    return chrome_options