#!/usr/bin/env python3
"""
GitLab MR Technical Documentation Generator
Automatically generates technical documentation from GitLab Merge Requests
Supports integration with Gemini Pro via browser automation
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import logging
from urllib.parse import urljoin, urlparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MRData:
    """Data structure for Merge Request information"""
    id: str
    title: str
    description: str
    author: str
    created_at: str
    merged_at: Optional[str]
    target_branch: str
    source_branch: str
    labels: List[str]
    changes: List[Dict]
    commits: List[Dict]
    files_changed: List[str]
    url: str
    project_type: str  # 'react' or 'spring-boot'

class GitLabScraper:
    """Scrapes GitLab MR information without API access"""
    
    def __init__(self, gitlab_base_url: str, session: Optional[requests.Session] = None):
        self.base_url = gitlab_base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_mr_data(self, mr_url: str) -> Optional[MRData]:
        """Extract MR data from GitLab page"""
        try:
            response = self.session.get(mr_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic information
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            author = self._extract_author(soup)
            created_at = self._extract_created_date(soup)
            merged_at = self._extract_merged_date(soup)
            branches = self._extract_branches(soup)
            labels = self._extract_labels(soup)
            
            # Extract file changes
            files_changed = self._extract_changed_files(soup)
            
            # Determine project type
            project_type = self._determine_project_type(files_changed, title, description)
            
            # Extract MR ID from URL
            mr_id = self._extract_mr_id(mr_url)
            
            return MRData(
                id=mr_id,
                title=title,
                description=description,
                author=author,
                created_at=created_at,
                merged_at=merged_at,
                target_branch=branches.get('target', ''),
                source_branch=branches.get('source', ''),
                labels=labels,
                changes=[],  # Will be populated separately if needed
                commits=[],  # Will be populated separately if needed
                files_changed=files_changed,
                url=mr_url,
                project_type=project_type
            )
            
        except Exception as e:
            logger.error(f"Error extracting MR data from {mr_url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract MR title"""
        title_selectors = [
            'h1.title',
            '.merge-request-title',
            'h1',
            '.page-title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return "Unknown Title"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract MR description"""
        desc_selectors = [
            '.description .md',
            '.merge-request-description',
            '.description',
            '.js-task-list-container'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract MR author"""
        author_selectors = [
            '.author-link',
            '.merge-request-author',
            '.author'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return "Unknown Author"
    
    def _extract_created_date(self, soup: BeautifulSoup) -> str:
        """Extract creation date"""
        date_selectors = [
            'time[datetime]',
            '.created-at time',
            '.merge-request-info time'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get('datetime', element.get_text(strip=True))
        return ""
    
    def _extract_merged_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract merge date if merged"""
        merged_selectors = [
            '.merged-at time',
            '.status-box-merged time'
        ]
        
        for selector in merged_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get('datetime', element.get_text(strip=True))
        return None
    
    def _extract_branches(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract source and target branches"""
        branches = {'source': '', 'target': ''}
        
        # Look for branch information
        branch_elements = soup.select('.branch-link, .ref-name')
        if len(branch_elements) >= 2:
            branches['source'] = branch_elements[0].get_text(strip=True)
            branches['target'] = branch_elements[1].get_text(strip=True)
        
        return branches
    
    def _extract_labels(self, soup: BeautifulSoup) -> List[str]:
        """Extract MR labels"""
        labels = []
        label_elements = soup.select('.label, .badge')
        
        for element in label_elements:
            label_text = element.get_text(strip=True)
            if label_text and label_text not in labels:
                labels.append(label_text)
        
        return labels
    
    def _extract_changed_files(self, soup: BeautifulSoup) -> List[str]:
        """Extract list of changed files"""
        files = []
        
        # Look for file paths in diffs
        file_selectors = [
            '.file-title-name',
            '.diff-file .file-title',
            '.js-file-title'
        ]
        
        for selector in file_selectors:
            elements = soup.select(selector)
            for element in elements:
                file_path = element.get_text(strip=True)
                if file_path and file_path not in files:
                    files.append(file_path)
        
        return files
    
    def _determine_project_type(self, files: List[str], title: str, description: str) -> str:
        """Determine if this is a React or Spring Boot project"""
        react_indicators = [
            '.jsx', '.tsx', '.js', '.ts', 'package.json', 'src/components',
            'react', 'redux', 'hooks', 'component'
        ]
        
        spring_indicators = [
            '.java', 'pom.xml', 'build.gradle', 'src/main/java',
            'spring', 'boot', 'controller', 'service', 'repository'
        ]
        
        text_to_check = ' '.join([title, description] + files).lower()
        
        react_score = sum(1 for indicator in react_indicators if indicator in text_to_check)
        spring_score = sum(1 for indicator in spring_indicators if indicator in text_to_check)
        
        if react_score > spring_score:
            return 'react'
        elif spring_score > react_score:
            return 'spring-boot'
        else:
            return 'unknown'
    
    def _extract_mr_id(self, url: str) -> str:
        """Extract MR ID from URL"""
        match = re.search(r'/merge_requests/(\d+)', url)
        return match.group(1) if match else url.split('/')[-1]

class GeminiProIntegration:
    """Integration with Gemini Pro via browser automation"""
    
    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def enhance_documentation(self, mr_data: MRData) -> str:
        """Use Gemini Pro to enhance MR documentation"""
        if not self.driver:
            return self._generate_basic_documentation(mr_data)
        
        try:
            # Navigate to Gemini Pro
            self.driver.get("https://gemini.google.com/")
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Prepare prompt for Gemini
            prompt = self._create_gemini_prompt(mr_data)
            
            # Find and fill the input field
            input_selectors = [
                'textarea[placeholder*="Enter a prompt"]',
                'textarea[data-testid="input-textarea"]',
                '.ql-editor',
                'div[contenteditable="true"]'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not input_element:
                logger.warning("Could not find Gemini input field, using basic documentation")
                return self._generate_basic_documentation(mr_data)
            
            # Clear and enter prompt
            input_element.clear()
            input_element.send_keys(prompt)
            
            # Submit the prompt
            submit_selectors = [
                'button[type="submit"]',
                'button[aria-label*="Send"]',
                '.send-button'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    submit_button.click()
                    break
                except NoSuchElementException:
                    continue
            
            # Wait for response
            time.sleep(5)
            
            # Extract response
            response_selectors = [
                '.response-content',
                '.markdown-content',
                '.message-content'
            ]
            
            for selector in response_selectors:
                try:
                    response_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    return response_element.text
                except TimeoutException:
                    continue
            
            logger.warning("Could not extract Gemini response, using basic documentation")
            return self._generate_basic_documentation(mr_data)
            
        except Exception as e:
            logger.error(f"Error with Gemini integration: {e}")
            return self._generate_basic_documentation(mr_data)
    
    def _create_gemini_prompt(self, mr_data: MRData) -> str:
        """Create a structured prompt for Gemini Pro"""
        return f"""
        Please generate comprehensive technical documentation for the following {mr_data.project_type} merge request:

        **Merge Request Details:**
        - Title: {mr_data.title}
        - Author: {mr_data.author}
        - Description: {mr_data.description}
        - Files Changed: {', '.join(mr_data.files_changed[:10])}
        - Labels: {', '.join(mr_data.labels)}

        **Please provide documentation including:**
        1. **Summary**: Brief overview of changes
        2. **Technical Details**: What was implemented/changed
        3. **Impact**: How this affects the system
        4. **Dependencies**: Any new dependencies or requirements
        5. **Testing**: Testing approach and coverage
        6. **Deployment Notes**: Any special deployment considerations

        Format the response in clear markdown with proper sections and bullet points.
        """
    
    def _generate_basic_documentation(self, mr_data: MRData) -> str:
        """Generate basic documentation without Gemini"""
        return f"""
# {mr_data.title}

**MR ID:** {mr_data.id}  
**Author:** {mr_data.author}  
**Project Type:** {mr_data.project_type.replace('-', ' ').title()}  
**Created:** {mr_data.created_at}  
**Status:** {'Merged' if mr_data.merged_at else 'Open'}

## Description
{mr_data.description or 'No description provided'}

## Files Changed
{chr(10).join(f'- {file}' for file in mr_data.files_changed[:20])}

## Labels
{', '.join(mr_data.labels) if mr_data.labels else 'No labels'}

## Branch Information
- **Source:** {mr_data.source_branch}
- **Target:** {mr_data.target_branch}

---
*Generated automatically from GitLab MR data*
        """
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()

class DocumentationGenerator:
    """Main class for generating technical documentation"""
    
    def __init__(self, gitlab_url: str, use_gemini: bool = True, headless: bool = True):
        self.gitlab_scraper = GitLabScraper(gitlab_url)
        self.gemini = GeminiProIntegration(headless=headless) if use_gemini else None
        self.processed_mrs = []
    
    def process_mr_list(self, mr_urls: List[str], output_dir: str = "documentation") -> None:
        """Process a list of MR URLs and generate documentation"""
        Path(output_dir).mkdir(exist_ok=True)
        
        logger.info(f"Processing {len(mr_urls)} merge requests...")
        
        for i, url in enumerate(mr_urls, 1):
            logger.info(f"Processing MR {i}/{len(mr_urls)}: {url}")
            
            try:
                # Extract MR data
                mr_data = self.gitlab_scraper.extract_mr_data(url)
                if not mr_data:
                    logger.warning(f"Could not extract data from {url}")
                    continue
                
                # Generate documentation
                if self.gemini:
                    documentation = self.gemini.enhance_documentation(mr_data)
                else:
                    documentation = self._generate_basic_doc(mr_data)
                
                # Save documentation
                filename = f"MR_{mr_data.id}_{mr_data.project_type}.md"
                filepath = Path(output_dir) / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(documentation)
                
                self.processed_mrs.append({
                    'id': mr_data.id,
                    'title': mr_data.title,
                    'type': mr_data.project_type,
                    'file': filename,
                    'url': url
                })
                
                logger.info(f"Documentation saved: {filepath}")
                
                # Small delay to be respectful
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                continue
        
        # Generate summary report
        self._generate_summary_report(output_dir)
        
        logger.info(f"Processing complete! Documentation saved in '{output_dir}' directory")
    
    def _generate_basic_doc(self, mr_data: MRData) -> str:
        """Generate basic documentation without Gemini"""
        return f"""
# {mr_data.title}

**MR ID:** {mr_data.id}  
**Author:** {mr_data.author}  
**Project Type:** {mr_data.project_type.replace('-', ' ').title()}  
**Created:** {mr_data.created_at}  
**Status:** {'Merged' if mr_data.merged_at else 'Open'}

## Description
{mr_data.description or 'No description provided'}

## Technical Changes

### Files Modified
{chr(10).join(f'- {file}' for file in mr_data.files_changed[:20])}

### Project Type Analysis
This merge request appears to be related to **{mr_data.project_type.replace('-', ' ').title()}** development based on the files changed and content analysis.

## Metadata
- **Source Branch:** {mr_data.source_branch}
- **Target Branch:** {mr_data.target_branch}
- **Labels:** {', '.join(mr_data.labels) if mr_data.labels else 'None'}
- **URL:** {mr_data.url}

---
*Generated automatically from GitLab MR data on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
        """
    
    def _generate_summary_report(self, output_dir: str) -> None:
        """Generate a summary report of all processed MRs"""
        if not self.processed_mrs:
            return
        
        # Create DataFrame for analysis
        df = pd.DataFrame(self.processed_mrs)
        
        # Generate summary
        summary = f"""# Technical Documentation Summary Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total MRs Processed:** {len(self.processed_mrs)}

## Project Type Breakdown
{df['type'].value_counts().to_string()}

## Processed Merge Requests

| MR ID | Title | Type | Documentation File |
|-------|-------|------|-------------------|
"""
        
        for mr in self.processed_mrs:
            title_truncated = mr['title'][:50] + '...' if len(mr['title']) > 50 else mr['title']
            summary += f"| {mr['id']} | {title_truncated} | {mr['type']} | [{mr['file']}](./{mr['file']}) |\n"
        
        # Save summary
        summary_path = Path(output_dir) / "README.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"Summary report saved: {summary_path}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.gemini:
            self.gemini.close()

def load_mr_urls_from_file(file_path: str) -> List[str]:
    """Load MR URLs from a text file"""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
    
    return urls

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Generate technical documentation from GitLab MRs')
    parser.add_argument('--gitlab-url', required=True, help='GitLab instance base URL')
    parser.add_argument('--mr-file', help='File containing MR URLs (one per line)')
    parser.add_argument('--mr-urls', nargs='+', help='Space-separated list of MR URLs')
    parser.add_argument('--output-dir', default='documentation', help='Output directory for documentation')
    parser.add_argument('--no-gemini', action='store_true', help='Skip Gemini Pro integration')
    parser.add_argument('--show-browser', action='store_true', help='Show browser during Gemini automation')
    
    args = parser.parse_args()
    
    # Get MR URLs
    mr_urls = []
    if args.mr_file:
        mr_urls.extend(load_mr_urls_from_file(args.mr_file))
    if args.mr_urls:
        mr_urls.extend(args.mr_urls)
    
    if not mr_urls:
        logger.error("No MR URLs provided. Use --mr-file or --mr-urls")
        return
    
    # Initialize generator
    use_gemini = not args.no_gemini
    headless = not args.show_browser
    
    generator = DocumentationGenerator(
        gitlab_url=args.gitlab_url,
        use_gemini=use_gemini,
        headless=headless
    )
    
    try:
        # Process MRs
        generator.process_mr_list(mr_urls, args.output_dir)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        generator.cleanup()

if __name__ == "__main__":
    main()
