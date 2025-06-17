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
    detailed_changes: List[Dict[str, Any]]  # Added for detailed change info

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
            
            # Get MR changes with diff content
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
            
            # Get discussions for additional context
            discussions = self.get_mr_discussions(project_id, mr_iid)
            
            # Process the data
            return self._process_mr_data(mr_info, changes_data, commits_data, project_info, discussions)
            
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
    
    def _process_mr_data(self, mr_info: Dict, changes_data: Dict, commits_data: List, project_info: Dict, discussions: List) -> MRData:
        """Process raw API data into MRData structure"""
        
        # Extract file changes with detailed diff information
        files_changed = []
        changes = []
        detailed_changes = []
        total_additions = 0
        total_deletions = 0
        
        for change in changes_data.get('changes', []):
            file_path = change.get('new_path') or change.get('old_path', '')
            if file_path:
                files_changed.append(file_path)
            
            # Get the diff content
            diff = change.get('diff', '')
            
            # Parse diff for additions/deletions
            diff_lines = diff.split('\n') if diff else []
            additions = len([line for line in diff_lines if line.startswith('+') and not line.startswith('+++')])
            deletions = len([line for line in diff_lines if line.startswith('-') and not line.startswith('---')])
            
            total_additions += additions
            total_deletions += deletions
            
            # Store basic change info
            changes.append({
                'file': file_path,
                'additions': additions,
                'deletions': deletions,
                'new_file': change.get('new_file', False),
                'renamed_file': change.get('renamed_file', False),
                'deleted_file': change.get('deleted_file', False)
            })
            
            # Store detailed change info with diff content
            detailed_changes.append({
                'file': file_path,
                'old_path': change.get('old_path'),
                'new_path': change.get('new_path'),
                'diff': diff,
                'additions': additions,
                'deletions': deletions,
                'new_file': change.get('new_file', False),
                'renamed_file': change.get('renamed_file', False),
                'deleted_file': change.get('deleted_file', False),
                'binary': change.get('binary', False),
                'too_large': change.get('too_large', False)
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
            pipeline_status=self._get_pipeline_status(mr_info),
            detailed_changes=detailed_changes
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
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            logger.info("Continuing without Gemini integration...")
            self.driver = None
    
    def enhance_documentation(self, mr_data: MRData) -> str:
        """Use Gemini Pro to enhance MR documentation"""
        if not self.driver:
            logger.warning("WebDriver not available, using enhanced documentation without Gemini")
            return self._generate_enhanced_documentation(mr_data)
        
        try:
            logger.info("Navigating to Gemini Pro...")
            # Navigate to Gemini Pro
            self.driver.get("https://gemini.google.com/")
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Prepare comprehensive prompt for Gemini
            prompt = self._create_comprehensive_gemini_prompt(mr_data)
            logger.info(f"Generated prompt with {len(prompt)} characters")
            
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
                    logger.info(f"Found input element with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not input_element:
                logger.warning("Could not find Gemini input field, using enhanced documentation")
                return self._generate_enhanced_documentation(mr_data)
            
            # Clear and enter prompt
            input_element.clear()
            input_element.send_keys(prompt)
            logger.info("Prompt entered into Gemini interface")
            
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
                    logger.info("Submit button clicked")
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not submitted:
                # Try pressing Enter
                input_element.send_keys('\n')
                logger.info("Attempted to submit with Enter key")
            
            # Wait for response with longer timeout
            logger.info("Waiting for Gemini response...")
            time.sleep(10)  # Increased wait time for processing
            
            # Extract response with multiple attempts
            response_selectors = [
                '[data-testid="response"]',
                '.response-content',
                '.markdown-content',
                '.message-content',
                '.model-response',
                '[role="main"] div[data-response]',
                '.conversation-turn-content'
            ]
            
            for selector in response_selectors:
                try:
                    response_element = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    response_text = response_element.text
                    if response_text and len(response_text) > 200:  # Ensure substantial response
                        logger.info(f"Successfully extracted Gemini response ({len(response_text)} characters)")
                        return response_text
                except TimeoutException:
                    continue
            
            # Try to get any text content from the page
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                # Look for response patterns in the page text
                if "technical documentation" in page_text.lower() or "merge request" in page_text.lower():
                    # Extract relevant parts
                    lines = page_text.split('\n')
                    response_lines = []
                    capturing = False
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['technical documentation', 'executive summary', 'implementation']):
                            capturing = True
                        if capturing:
                            response_lines.append(line)
                    
                    if response_lines:
                        extracted_response = '\n'.join(response_lines[:100])  # Limit to reasonable size
                        if len(extracted_response) > 200:
                            logger.info("Extracted response from page content")
                            return extracted_response
            except Exception as e:
                logger.error(f"Error extracting from page content: {e}")
            
            logger.warning("Could not extract valid Gemini response, using enhanced documentation")
            return self._generate_enhanced_documentation(mr_data)
            
        except Exception as e:
            logger.error(f"Error with Gemini integration: {e}")
            return self._generate_enhanced_documentation(mr_data)
    
    def _create_comprehensive_gemini_prompt(self, mr_data: MRData) -> str:
        """Create a comprehensive prompt for Gemini Pro with detailed changes"""
        files_summary = ', '.join(mr_data.files_changed[:15])
        if len(mr_data.files_changed) > 15:
            files_summary += f" and {len(mr_data.files_changed) - 15} more files"
        
        # Extract key changes for the prompt
        key_changes = self._extract_key_changes(mr_data.detailed_changes)
        commit_summaries = self._extract_commit_summaries(mr_data.commits)
        
        prompt = f"""Please generate comprehensive technical documentation for this {mr_data.project_type} merge request:

**Merge Request Overview:**
- Title: {mr_data.title}
- Author: {mr_data.author} (@{mr_data.author_username})
- Project: {mr_data.project_name} ({mr_data.project_type.upper()})
- State: {mr_data.state} | Merge Status: {mr_data.merge_status}
- Target Branch: {mr_data.target_branch} ← Source Branch: {mr_data.source_branch}
- Labels: {', '.join(mr_data.labels) if mr_data.labels else 'None'}

**Description:**
{mr_data.description[:1000] if mr_data.description else 'No description provided'}

**Change Statistics:**
- Files Modified: {len(mr_data.files_changed)}
- Lines Added: {mr_data.additions}
- Lines Removed: {mr_data.deletions}
- Commits: {len(mr_data.commits)}

**Files Changed:**
{files_summary}

**Key Code Changes:**
{key_changes}

**Recent Commits:**
{commit_summaries}

**Pipeline Status:** {mr_data.pipeline_status or 'Not available'}
**Milestone:** {mr_data.milestone or 'None'}

Please generate detailed technical documentation with these sections:

1. **Executive Summary**: High-level overview of what this MR accomplishes
2. **Technical Implementation Details**: Specific changes made, technologies used
3. **Architecture & Design Impact**: How this affects the overall system architecture
4. **Code Quality & Best Practices**: Assessment of code quality and adherence to best practices
5. **Dependencies & Integration**: New dependencies, API changes, integration points
6. **Testing Strategy & Coverage**: Testing approach and recommendations
7. **Deployment Considerations**: Important notes for deployment and rollback
8. **Performance & Security Impact**: Performance implications and security considerations
9. **Risks & Mitigations**: Potential issues and how to address them
10. **Future Considerations**: Recommendations for future development

Format as clear, professional markdown with proper headers, bullet points, and code blocks where appropriate. Focus on technical accuracy and practical insights for developers and stakeholders.
"""
        
        return prompt
    
    def _extract_key_changes(self, detailed_changes: List[Dict]) -> str:
        """Extract key changes from detailed diff information"""
        if not detailed_changes:
            return "No detailed change information available"
        
        key_changes = []
        
        # Prioritize important files and changes
        for change in detailed_changes[:10]:  # Limit to top 10 changes
            file_path = change.get('file', '')
            diff = change.get('diff', '')
            
            if not diff or change.get('binary') or change.get('too_large'):
                continue
            
            # Extract meaningful lines from diff
            diff_lines = diff.split('\n')
            added_lines = [line[1:].strip() for line in diff_lines if line.startswith('+') and not line.startswith('+++') and line.strip()]
            removed_lines = [line[1:].strip() for line in diff_lines if line.startswith('-') and not line.startswith('---') and line.strip()]
            
            if added_lines or removed_lines:
                change_summary = f"\n**{file_path}:**"
                if change.get('new_file'):
                    change_summary += " (New file)"
                elif change.get('deleted_file'):
                    change_summary += " (Deleted)"
                elif change.get('renamed_file'):
                    change_summary += " (Renamed)"
                
                # Show key added/removed lines (limit to avoid too much text)
                if added_lines:
                    key_additions = added_lines[:3]  # Show first 3 additions
                    change_summary += f"\n  Added: {'; '.join(key_additions)}"
                    if len(added_lines) > 3:
                        change_summary += f" ... and {len(added_lines) - 3} more"
                
                if removed_lines:
                    key_removals = removed_lines[:3]  # Show first 3 removals
                    change_summary += f"\n  Removed: {'; '.join(key_removals)}"
                    if len(removed_lines) > 3:
                        change_summary += f" ... and {len(removed_lines) - 3} more"
                
                key_changes.append(change_summary)
        
        return '\n'.join(key_changes) if key_changes else "No significant code changes detected"
    
    def _extract_commit_summaries(self, commits: List[Dict]) -> str:
        """Extract commit summaries for context"""
        if not commits:
            return "No commit information available"
        
        summaries = []
        for commit in commits[:5]:  # Show first 5 commits
            title = commit.get('title', 'No title')
            author = commit.get('author_name', 'Unknown')
            date = commit.get('authored_date', '')[:10] if commit.get('authored_date') else ''
            short_id = commit.get('short_id', '')
            
            summaries.append(f"- {short_id}: {title} - {author} ({date})")
        
        if len(commits) > 5:
            summaries.append(f"... and {len(commits) - 5} more commits")
        
        return '\n'.join(summaries)
    
    def _create_gemini_prompt(self, mr_data: MRData) -> str:
        """Create a structured prompt for Gemini Pro (fallback method)"""
        return self._create_comprehensive_gemini_prompt(mr_data)
    
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

### Detailed Changes
{self._generate_detailed_changes_summary(mr_data.detailed_changes)}

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
    
    def _generate_detailed_changes_summary(self, detailed_changes: List[Dict]) -> str:
        """Generate summary of detailed changes"""
        if not detailed_changes:
            return "No detailed change information available"
        
        summary = []
        
        # Group changes by type
        new_files = [c for c in detailed_changes if c.get('new_file')]
        deleted_files = [c for c in detailed_changes if c.get('deleted_file')]
        renamed_files = [c for c in detailed_changes if c.get('renamed_file')]
        modified_files = [c for c in detailed_changes if not any([c.get('new_file'), c.get('deleted_file'), c.get('renamed_file')])]
        
        if new_files:
            summary.append(f"**New Files ({len(new_files)}):**")
            for nf in new_files[:5]:
                summary.append(f"- `{nf.get('file')}` (+{nf.get('additions', 0)} lines)")
            if len(new_files) > 5:
                summary.append(f"- ... and {len(new_files) - 5} more new files")
        
        if deleted_files:
            summary.append(f"**Deleted Files ({len(deleted_files)}):**")
            for df in deleted_files[:5]:
                summary.append(f"- `{df.get('file')}` (-{df.get('deletions', 0)} lines)")
            if len(deleted_files) > 5:
                summary.append(f"- ... and {len(deleted_files) - 5} more deleted files")
        
        if renamed_files:
            summary.append(f"**Renamed Files ({len(renamed_files)}):**")
            for rf in renamed_files[:5]:
                old_path = rf.get('old_path', 'unknown')
                new_path = rf.get('new_path', 'unknown')
                summary.append(f"- `{old_path}` → `{new_path}`")
            if len(renamed_files) > 5:
                summary.append(f"- ... and {len(renamed_files) - 5} more renamed files")
        
        if modified_files:
            summary.append(f"**Modified Files ({len(modified_files)}):**")
            # Show top modified files by change volume
            sorted_modified = sorted(modified_files, key=lambda x: x.get('additions', 0) + x.get('deletions', 0), reverse=True)
            for mf in sorted_modified[:10]:
                changes = mf.get('additions', 0) + mf.get('deletions', 0)
                summary.append(f"- `{mf.get('file')}` (+{mf.get('additions', 0)}/-{mf.get('deletions', 0)}) {changes} changes")
            if len(modifie