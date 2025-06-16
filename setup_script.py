#!/usr/bin/env python3
"""
Setup script for GitLab MR Documentation Generator
This script will help you set up all required dependencies
"""

import subprocess
import sys
import os
import platform
import requests
import zipfile
import shutil
from pathlib import Path

def install_pip_packages():
    """Install required Python packages"""
    print("Installing Python packages...")
    packages = [
        'selenium==4.15.2',
        'webdriver-manager==4.0.1',
        'requests==2.31.0'
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")
            return False
    
    return True

def check_chrome_installation():
    """Check if Chrome is installed"""
    print("\nChecking Chrome installation...")
    
    chrome_paths = []
    system = platform.system().lower()
    
    if system == 'windows':
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
        ]
    elif system == 'darwin':  # macOS
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    else:  # Linux
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium"
        ]
    
    for path in chrome_paths:
        expanded_path = os.path.expandvars(path)
        if os.path.exists(expanded_path):
            print(f"✓ Chrome found at: {expanded_path}")
            return True
    
    print("✗ Chrome not found. Please install Google Chrome:")
    print("  https://www.google.com/chrome/")
    return False

def get_chrome_version():
    """Get Chrome version"""
    try:
        if platform.system().lower() == 'windows':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version = winreg.QueryValueEx(key, "version")[0]
            return version
        else:
            # For Linux/Mac, try to get version from command line
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.split()[-1]
    except:
        pass
    
    return None

def download_chromedriver():
    """Download ChromeDriver manually"""
    print("\nAttempting to download ChromeDriver...")
    
    try:
        # Get latest ChromeDriver version
        response = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE')
        latest_version = response.text.strip()
        
        system = platform.system().lower()
        if system == 'windows':
            driver_url = f'https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_win32.zip'
            driver_name = 'chromedriver.exe'
        elif system == 'darwin':
            driver_url = f'https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_mac64.zip'
            driver_name = 'chromedriver'
        else:
            driver_url = f'https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_linux64.zip'
            driver_name = 'chromedriver'
        
        # Download ChromeDriver
        print(f"Downloading ChromeDriver {latest_version}...")
        response = requests.get(driver_url)
        
        with open('chromedriver.zip', 'wb') as f:
            f.write(response.content)
        
        # Extract ChromeDriver
        with zipfile.ZipFile('chromedriver.zip', 'r') as zip_ref:
            zip_ref.extractall('.')
        
        # Make executable on Unix systems
        if system != 'windows':
            os.chmod(driver_name, 0o755)
        
        # Clean up
        os.remove('chromedriver.zip')
        
        print(f"✓ ChromeDriver downloaded successfully: {driver_name}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to download ChromeDriver: {e}")
        return False

def test_setup():
    """Test the setup"""
    print("\nTesting setup...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Try with WebDriver Manager first
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get('https://www.google.com')
            driver.quit()
            print("✓ WebDriver Manager setup successful")
            return True
        except Exception as e:
            print(f"WebDriver Manager failed: {e}")
            
            # Try with local ChromeDriver
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.get('https://www.google.com')
                driver.quit()
                print("✓ Local ChromeDriver setup successful")
                return True
            except Exception as e2:
                print(f"✗ Setup test failed: {e2}")
                return False
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def main():
    """Main setup function"""
    print("GitLab MR Documentation Generator Setup")
    print("=" * 40)
    
    # Step 1: Install Python packages
    if not install_pip_packages():
        print("\n❌ Failed to install required packages")
        return False
    
    # Step 2: Check Chrome installation
    if not check_chrome_installation():
        print("\n❌ Chrome installation required")
        return False
    
    # Step 3: Test setup
    if test_setup():
        print("\n✅ Setup completed successfully!")
        print("\nYou can now run the GitLab MR Documentation Generator:")
        print("python gitlab_mr_doc_generator.py")
        return True
    else:
        print("\n⚠️  Setup test failed. Trying to download ChromeDriver manually...")
        if download_chromedriver():
            if test_setup():
                print("\n✅ Setup completed successfully with manual ChromeDriver!")
                return True
        
        print("\n❌ Setup failed. Please check the troubleshooting guide.")
        print_troubleshooting_guide()
        return False

def print_troubleshooting_guide():
    """Print troubleshooting guide"""
    print("\n" + "=" * 50)
    print("TROUBLESHOOTING GUIDE")
    print("=" * 50)
    print("\n1. Make sure Google Chrome is installed")
    print("2. Try running: pip install --upgrade selenium webdriver-manager")
    print("3. Check firewall/antivirus settings")
    print("4. Try running as administrator (Windows)")
    print("5. Check Chrome version compatibility")
    print("\nFor more help, visit:")
    print("https://selenium-python.readthedocs.io/installation.html")

if __name__ == "__main__":
    main()