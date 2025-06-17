#!/usr/bin/env python3
"""
GitLab MR Technical Documentation Generator (API Version)
Automatically generates technical documentation from GitLab Merge Requests using API
Supports integration with Gemini Pro via browser automation
"""

import requests
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
import argparse
import os
from dataclasses import dataclass, asdict
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
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MRData:
    """Data structure for Merge Request information"""
    id: int
    iid: int
    title: str
    description: str
    author: str
    author_username: str
    created_at: str
    updated_at: str
    merged_at: Optional[str]
    closed_at: Optional[str]
    target_branch: str
    source_branch: str
    labels: List[str]
    assignees: List[str]
    reviewers: List[str]
    state: str
    merge_status: str
    changes: List[Dict[str, Any]]
    commits: List[Dict[str, Any]]
    files_changed: List[str]
    additions: int
    deletions: int
    url: str
    web_url: str
    project_name: str
    project_path: str
    project_type: str  # 'react', 'spring-boot', or 'mixed'
    milestone: Optional[str]
    pipeline_status: Optional[str]

class GitLabAPIClient:
    """GitLab API client for fetching MR information"""
    
    def __init__(self, gitlab_url: str, private_token: str):
        self.base_url = gitlab_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v4"
        self.private_token = private_token
        self.session = requests.Session()
        self.session.headers.update({
            'PRIVATE-TOKEN': private_token,
            'Content-Type': 'application/json'
        })
    
    def get_mr_data(self, project_id: str, mr_iid: int) -> Optional[MRData]:
        """Fetch complete MR data from GitLab API"""
        try:
            # Get basic MR info
            mr_url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}"
            response = self.session.get(mr_url)
            response.raise_for_status()
            mr_info = response.json()
            
            # Get MR changes
            changes_url = f"{mr_url}/changes"
            changes_response = self.session.get(changes_url)
            changes_response.raise_for_status()
            changes_data = changes_response.json()
            
            # Get MR commits
            commits_url = f"{mr_url}/commits"
            commits_response = self.session.get(commits_url)
            commits_response.raise_for_status()
            commits_data = commits_response.json()
            
            # Get project info
            project_info = self.get_project_info(project_id)
            
            # Process the data
            return self._process_mr_data(mr_info, changes_data, commits_data, project_info)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for MR {mr_iid} in project {project_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing MR data: {e}")
            return None
    
    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """Get project information"""
        try:
            project_url = f"{self.api_url}/projects/{project_id}"
            response = self.session.get(project_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching project info: {e}")
            return {}
    
    def get_mr_discussions(self, project_id: str, mr_iid: int) -> List[Dict[str, Any]]:
        """Get MR discussions/comments"""
        try:
            discussions_url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/discussions"
            response = self.session.get(discussions_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching discussions: {e}")
            return []
    
    def _process_mr_data(self, mr_info: Dict, changes_data: Dict, commits_data: List, project_info: Dict) -> MRData:
        """Process raw API data into MRData structure"""
        
        # Extract file changes
        files_changed = []
        changes = []
        total_additions = 0
        total_deletions = 0
        
        for change in changes_data.get('changes', []):
            file_path = change.get('new_path') or change.get('old_path', '')
            if file_path:
                files_changed.append(file_path)
            
            # Count additions and deletions
            diff = change.get('diff', '')
            additions = len([line for line in diff.split('\n') if line.startswith('+')])
            deletions = len([line for line in diff.split('\n') if line.startswith('-')])
            total_additions += additions
            total_deletions += deletions
            
            changes.append({
                'file': file_path,
                'additions': additions,
                'deletions': deletions,
                'new_file': change.get('new_file', False),
                'renamed_file': change.get('renamed_file', False),
                'deleted_file': change.get('deleted_file', False)
            })
        
        # Process commits
        processed_commits = []
        for commit in commits_data:
            processed_commits.append({
                'id': commit.get('id'),
                'short_id': commit.get('short_id'),
                'title': commit.get('title'),
                'message': commit.get('message'),
                'author_name': commit.get('author_name'),
                'authored_date': commit.get('authored_date'),
                'committer_name': commit.get('committer_name'),
                'committed_date': commit.get('committed_date')
            })
        
        # Determine project type
        project_type = self._determine_project_type(files_changed, mr_info.get('title', ''), mr_info.get('description', ''))
        
        # Extract labels
        labels = [label.get('name', '') for label in mr_info.get('labels', [])]
        
        # Extract assignees and reviewers
        assignees = [assignee.get('name', '') for assignee in mr_info.get('assignees', [])]
        reviewers = [reviewer.get('name', '') for reviewer in mr_info.get('reviewers', [])]
        
        return MRData(
            id=mr_info.get('id'),
            iid=mr_info.get('iid'),
            title=mr_info.get('title', ''),
            description=mr_info.get('description', ''),
            author=mr_info.get('author', {}).get('name', ''),
            author_username=mr_info.get('author', {}).get('username', ''),
            created_at=mr_info.get('created_at', ''),
            updated_at=mr_info.get('updated_at', ''),
            merged_at=mr_info.get('merged_at'),
            closed_at=mr_info.get('closed_at'),
            target_branch=mr_info.get('target_branch', ''),
            source_branch=mr_info.get('source_branch', ''),
            labels=labels,
            assignees=assignees,
            reviewers=reviewers,
            state=mr_info.get('state', ''),
            merge_status=mr_info.get('merge_status', ''),
            changes=changes,
            commits=processed_commits,
            files_changed=files_changed,
            additions=total_additions,
            deletions=total_deletions,
            url=mr_info.get('web_url', ''),
            web_url=mr_info.get('web_url', ''),
            project_name=project_info.get('name', ''),
            project_path=project_info.get('path_with_namespace', ''),
            project_type=project_type,
            milestone=mr_info.get('milestone', {}).get('title') if mr_info.get('milestone') else None,
            pipeline_status=self._get_pipeline_status(mr_info)
        )
    
    def _determine_project_type(self, files: List[str], title: str, description: str) -> str:
        """Determine if this is a React, Spring Boot, or mixed project"""
        react_indicators = [
            '.jsx', '.tsx', '.js', '.ts', 'package.json', 'src/components',
            'src/hooks', 'src/pages', 'src/utils', 'public/', 'node_modules',
            'yarn.lock', 'package-lock.json', '.env', 'webpack', 'vite'
        ]
        
        spring_indicators = [
            '.java', 'pom.xml', 'build.gradle', 'src/main/java', 'src/test/java',
            'src/main/resources', 'application.properties', 'application.yml',
            'target/', 'build/', '.mvn', 'gradlew'
        ]
        
        text_to_check = ' '.join([title, description] + files).lower()
        
        react_matches = sum(1 for indicator in react_indicators if indicator.lower() in text_to_check)
        spring_matches = sum(1 for indicator in spring_indicators if indicator.lower() in text_to_check)
        
        if react_matches > 0 and spring_matches > 0:
            return 'mixed'
        elif react_matches > spring_matches:
            return 'react'
        elif spring_matches > react_matches:
            return 'spring-boot'
        else:
            return 'unknown'
    
    def _get_pipeline_status(self, mr_info: Dict) -> Optional[str]:
        """Extract pipeline status"""
        pipeline = mr_info.get('pipeline')
        if pipeline:
            return pipeline.get('status')
        return None
    
    def parse_mr_url(self, mr_url: str) -> Optional[tuple]:
        """Parse MR URL to extract project ID and MR IID"""
        # Pattern for GitLab MR URLs: https://gitlab.com/group/project/-/merge_requests/123
        pattern = r'https?://[^/]+/(.+?)/-/merge_requests/(\d+)'
        match = re.match(pattern, mr_url)
        
        if match:
            project_path = match.group(1)
            mr_iid = int(match.group(2))
            # URL encode the project path
            project_id = requests.utils.quote(project_path, safe='')
            return project_id, mr_iid
        
        logger.error(f"Could not parse MR URL: {mr_url}")
        return None

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
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            logger.info("Continuing without Gemini integration...")
            self.driver = None
    
    def enhance_documentation(self, mr_data: MRData) -> str:
        """Use Gemini Pro to enhance MR documentation"""
        if not self.driver:
            return self._generate_enhanced_documentation(mr_data)
        
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
                'div[contenteditable="true"]',
                'textarea'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not input_element:
                logger.warning("Could not find Gemini input field, using enhanced documentation")
                return self._generate_enhanced_documentation(mr_data)
            
            # Clear and enter prompt
            input_element.clear()
            input_element.send_keys(prompt)
            
            # Find and click submit button
            submit_selectors = [
                'button[type="submit"]',
                'button[aria-label*="Send"]',
                'button[data-testid="send-button"]',
                '.send-button'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    submit_button.click()
                    submitted = True
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not submitted:
                # Try pressing Enter
                input_element.send_keys('\n')
            
            # Wait for response
            time.sleep(8)
            
            # Extract response
            response_selectors = [
                '[data-testid="response"]',
                '.response-content',
                '.markdown-content',
                '.message-content',
                '.model-response'
            ]
            
            for selector in response_selectors:
                try:
                    response_element = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    response_text = response_element.text
                    if response_text and len(response_text) > 100:
                        return response_text
                except TimeoutException:
                    continue
            
            logger.warning("Could not extract Gemini response, using enhanced documentation")
            return self._generate_enhanced_documentation(mr_data)
            
        except Exception as e:
            logger.error(f"Error with Gemini integration: {e}")
            return self._generate_enhanced_documentation(mr_data)
    
    def _create_gemini_prompt(self, mr_data: MRData) -> str:
        """Create a structured prompt for Gemini Pro"""
        files_summary = ', '.join(mr_data.files_changed[:15])
        if len(mr_data.files_changed) > 15:
            files_summary += f" and {len(mr_data.files_changed) - 15} more files"
        
        return f"""
Please generate comprehensive technical documentation for this {mr_data.project_type} merge request:

**Merge Request Details:**
- Title: {mr_data.title}
- Author: {mr_data.author}
- Project: {mr_data.project_name}
- Description: {mr_data.description[:500]}...
- Files Changed: {files_summary}
- Lines Added: {mr_data.additions}, Lines Removed: {mr_data.deletions}
- Labels: {', '.join(mr_data.labels)}
- State: {mr_data.state}

**Generate documentation with these sections:**
1. **Executive Summary**: High-level overview
2. **Technical Implementation**: What was built/changed
3. **Architecture Impact**: How this affects the system
4. **Dependencies & Requirements**: New dependencies or changes
5. **Testing Strategy**: How this should be tested
6. **Deployment Considerations**: Important deployment notes
7. **Risks & Mitigations**: Potential issues and solutions

Format as clear markdown with proper headers and bullet points.
        """
    
    def _generate_enhanced_documentation(self, mr_data: MRData) -> str:
        """Generate enhanced documentation without Gemini"""
        status_emoji = {
            'merged': '✅',
            'opened': '🔄',
            'closed': '❌'
        }.get(mr_data.state, '📝')
        
        pipeline_status = f"**Pipeline:** {mr_data.pipeline_status}" if mr_data.pipeline_status else ""
        milestone_info = f"**Milestone:** {mr_data.milestone}" if mr_data.milestone else ""
        
        return f"""# {status_emoji} {mr_data.title}

## Overview
**MR !{mr_data.iid}** | **Project:** {mr_data.project_name} | **Type:** {mr_data.project_type.replace('-', ' ').title()}  
**Author:** {mr_data.author} (@{mr_data.author_username})  
**Created:** {mr_data.created_at[:10]} | **Updated:** {mr_data.updated_at[:10]}  
**Status:** {mr_data.state.title()} | **Merge Status:** {mr_data.merge_status}  
{pipeline_status}  
{milestone_info}

## Description
{mr_data.description or 'No description provided'}

## Technical Summary
- **Files Modified:** {len(mr_data.files_changed)} files
- **Lines Added:** {mr_data.additions}
- **Lines Removed:** {mr_data.deletions}
- **Commits:** {len(mr_data.commits)}

## Changes Overview

### Modified Files
{chr(10).join(f'- `{file}`' for file in mr_data.files_changed[:25])}
{f'... and {len(mr_data.files_changed) - 25} more files' if len(mr_data.files_changed) > 25 else ''}

### File Type Analysis
{self._generate_file_analysis(mr_data.changes)}

## Commit History
{self._generate_commit_summary(mr_data.commits[:10])}

## Branch Information
- **Source Branch:** `{mr_data.source_branch}`
- **Target Branch:** `{mr_data.target_branch}`

## Metadata
- **Labels:** {', '.join(mr_data.labels) if mr_data.labels else 'None'}
- **Assignees:** {', '.join(mr_data.assignees) if mr_data.assignees else 'None'}
- **Reviewers:** {', '.join(mr_data.reviewers) if mr_data.reviewers else 'None'}
- **GitLab URL:** [View MR]({mr_data.web_url})

## Impact Assessment
{self._generate_impact_assessment(mr_data)}

---
*Generated automatically from GitLab API on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
        """
    
    def _generate_file_analysis(self, changes: List[Dict]) -> str:
        """Generate analysis of file changes"""
        if not changes:
            return "No detailed change information available"
        
        new_files = [c for c in changes if c.get('new_file')]
        deleted_files = [c for c in changes if c.get('deleted_file')]
        renamed_files = [c for c in changes if c.get('renamed_file')]
        modified_files = [c for c in changes if not any([c.get('new_file'), c.get('deleted_file'), c.get('renamed_file')])]
        
        analysis = []
        if new_files:
            analysis.append(f"- **New Files:** {len(new_files)} files created")
        if deleted_files:
            analysis.append(f"- **Deleted Files:** {len(deleted_files)} files removed")
        if renamed_files:
            analysis.append(f"- **Renamed Files:** {len(renamed_files)} files renamed")
        if modified_files:
            analysis.append(f"- **Modified Files:** {len(modified_files)} files changed")
        
        return '\n'.join(analysis) if analysis else "No change type information available"
    
    def _generate_commit_summary(self, commits: List[Dict]) -> str:
        """Generate commit summary"""
        if not commits:
            return "No commit information available"
        
        summary = []
        for commit in commits[:5]:  # Show first 5 commits
            title = commit.get('title', 'No title')[:60]
            short_id = commit.get('short_id', '')
            author = commit.get('author_name', 'Unknown')
            summary.append(f"- `{short_id}` {title} - *{author}*")
        
        if len(commits) > 5:
            summary.append(f"... and {len(commits) - 5} more commits")
        
        return '\n'.join(summary)
    
    def _generate_impact_assessment(self, mr_data: MRData) -> str:
        """Generate impact assessment based on changes"""
        impact = []
        
        # Size-based assessment
        total_changes = mr_data.additions + mr_data.deletions
        if total_changes > 1000:
            impact.append("🔴 **High Impact**: Large changeset with 1000+ line changes")
        elif total_changes > 500:
            impact.append("🟡 **Medium Impact**: Moderate changeset with 500+ line changes")
        else:
            impact.append("🟢 **Low Impact**: Small changeset with minimal changes")
        
        # File-based assessment
        if len(mr_data.files_changed) > 20:
            impact.append("📁 **Multiple Components**: Changes span across many files")
        
        # Project type specific assessment
        if mr_data.project_type == 'react':
            impact.append("⚛️ **Frontend Impact**: React application changes")
        elif mr_data.project_type == 'spring-boot':
            impact.append("🍃 **Backend Impact**: Spring Boot application changes")
        elif mr_data.project_type == 'mixed':
            impact.append("🔄 **Full Stack Impact**: Both frontend and backend changes")
        
        return '\n'.join(impact) if impact else "Impact assessment not available"
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

class DocumentationGenerator:
    """Main class for generating technical documentation"""
    
    def __init__(self, gitlab_url: str, private_token: str, use_gemini: bool = True, headless: bool = True):
        self.gitlab_client = GitLabAPIClient(gitlab_url, private_token)
        self.gemini = GeminiProIntegration(headless=headless) if use_gemini else None
        self.processed_mrs = []
        self.failed_mrs = []
    
    def process_mr_list(self, mr_urls: List[str], output_dir: str = "documentation") -> None:
        """Process a list of MR URLs and generate documentation"""
        Path(output_dir).mkdir(exist_ok=True)
        
        logger.info(f"Processing {len(mr_urls)} merge requests...")
        
        for i, url in enumerate(mr_urls, 1):
            logger.info(f"Processing MR {i}/{len(mr_urls)}: {url}")
            
            try:
                # Parse MR URL
                parsed = self.gitlab_client.parse_mr_url(url)
                if not parsed:
                    self.failed_mrs.append({'url': url, 'reason': 'Invalid URL format'})
                    continue
                
                project_id, mr_iid = parsed
                
                # Extract MR data via API
                mr_data = self.gitlab_client.get_mr_data(project_id, mr_iid)
                if not mr_data:
                    self.failed_mrs.append({'url': url, 'reason': 'Failed to fetch MR data'})
                    continue
                
                # Generate documentation
                if self.gemini:
                    documentation = self.gemini.enhance_documentation(mr_data)
                else:
                    documentation = self._generate_basic_doc(mr_data)
                
                # Save documentation
                filename = f"MR_{mr_data.iid}_{mr_data.project_type}_{mr_data.project_name.replace('/', '_')}.md"
                # Sanitize filename
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                filepath = Path(output_dir) / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(documentation)
                
                self.processed_mrs.append({
                    'id': mr_data.id,
                    'iid': mr_data.iid,
                    'title': mr_data.title,
                    'type': mr_data.project_type,
                    'project': mr_data.project_name,
                    'file': filename,
                    'url': url,
                    'state': mr_data.state,
                    'additions': mr_data.additions,
                    'deletions': mr_data.deletions,
                    'files_changed': len(mr_data.files_changed)
                })
                
                logger.info(f"Documentation saved: {filepath}")
                
                # Small delay to be respectful to GitLab API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                self.failed_mrs.append({'url': url, 'reason': str(e)})
                continue
        
        # Generate summary report
        self._generate_summary_report(output_dir)
        
        success_count = len(self.processed_mrs)
        failed_count = len(self.failed_mrs)
        logger.info(f"Processing complete! {success_count} successful, {failed_count} failed")
        logger.info(f"Documentation saved in '{output_dir}' directory")
    
    def _generate_basic_doc(self, mr_data: MRData) -> str:
        """Generate basic documentation without Gemini"""
        gemini_integration = GeminiProIntegration(headless=True)
        doc = gemini_integration._generate_enhanced_documentation(mr_data)
        gemini_integration.close()
        return doc
    
    def _generate_summary_report(self, output_dir: str) -> None:
        """Generate a comprehensive summary report"""
        if not self.processed_mrs and not self.failed_mrs:
            return
        
        # Create DataFrame for analysis
        if self.processed_mrs:
            df = pd.DataFrame(self.processed_mrs)
        
        # Generate summary
        summary = f"""# Technical Documentation Summary Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total MRs Processed:** {len(self.processed_mrs)}  
**Failed MRs:** {len(self.failed_mrs)}

"""
        
        if self.processed_mrs:
            # Project statistics
            summary += f"""## Statistics

### Project Type Distribution
{df['type'].value_counts().to_string()}

### State Distribution
{df['state'].value_counts().to_string()}

### Change Size Analysis
- **Total Lines Added:** {df['additions'].sum():,}
- **Total Lines Removed:** {df['deletions'].sum():,}
- **Average Files per MR:** {df['files_changed'].mean():.1f}
- **Largest MR:** {df['additions'].max() + df['deletions'].max():,} lines

"""
        
        # Processed MRs table
        if self.processed_mrs:
            summary += """## Successfully Processed Merge Requests

| MR | Title | Project | Type | State | Changes | Files | Documentation |
|----|-------|---------|------|-------|---------|-------|---------------|
"""
            
            for mr in self.processed_mrs:
                title_truncated = mr['title'][:40] + '...' if len(mr['title']) > 40 else mr['title']
                project_truncated = mr['project'][:20] + '...' if len(mr['project']) > 20 else mr['project']
                changes = mr['additions'] + mr['deletions']
                summary += f"| !{mr['iid']} | {title_truncated} | {project_truncated} | {mr['type']} | {mr['state']} | +{mr['additions']}/-{mr['deletions']} | {mr['files_changed']} | [{mr['file']}](./{mr['file']}) |\n"
        
        # Failed MRs
        if self.failed_mrs:
            summary += f"""
## Failed Processing ({len(self.failed_mrs)} MRs)

| URL | Reason |
|-----|--------|
"""
            for failed in self.failed_mrs:
                url_truncated = failed['url'][-50:] if len(failed['url']) > 50 else failed['url']
                summary += f"| {url_truncated} | {failed['reason']} |\n"
        
        summary += f"""
## Usage Instructions

1. **Individual Documentation**: Each MR has its own detailed documentation file
2. **File Naming**: `MR_{{iid}}_{{type}}_{{project}}.md`
3. **Content**: Each file contains technical analysis, impact assessment, and change details
4. **API Source**: All data extracted using GitLab API for accuracy

Generated using GitLab API with private token authentication.
"""
        
        # Save summary
        summary_path = Path(output_dir) / "README.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        # Save raw data as JSON for further analysis
        data_path = Path(output_dir) / "raw_data.json"
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_mrs': self.processed_mrs,
                'failed_mrs': self.failed_mrs,
                'generated_at': datetime.now().isoformat()
            