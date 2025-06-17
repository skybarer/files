logger.warning("⚠️  Could not locate Gemini input area reliably")
                logger.info("The interface may still work, but manual intervention might be needed")
                self.gemini_ready = False

            return input_found

        except Exception as e:
            logger.error(f"❌ Error setting up Gemini interface: {e}")
            self.gemini_ready = False
            return False

    def get_merge_request_changes(self, project_id: str, mr_iid: str) -> List[Dict]:
        """Get the file changes for a merge request with enhanced file type detection"""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
            verify_ssl = getattr(self, 'ssl_verify', True)
            response = requests.get(url, headers=self.headers, timeout=30, verify=verify_ssl)

            if response.status_code == 200:
                changes_data = response.json()
                return self.process_file_changes(changes_data.get('changes', []))
            else:
                logger.error(f"Failed to get changes: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting MR changes: {e}")
            return []

    def process_file_changes(self, changes: List[Dict]) -> List[Dict]:
        """Process and categorize file changes with enhanced type detection"""
        processed_changes = []
        
        for change in changes:
            file_path = change.get('new_path') or change.get('old_path', '')
            
            # Enhanced file categorization
            file_info = self.analyze_file_type(file_path, change.get('diff', ''))
            
            processed_change = {
                'file_path': file_path,
                'change_type': self.determine_change_type(change),
                'file_type': file_info['type'],
                'file_category': file_info['category'],
                'frameworks': file_info['frameworks'],
                'diff': change.get('diff', ''),
                'additions': change.get('new_file', False),
                'deletions': change.get('deleted_file', False),
                'renamed': change.get('renamed_file', False)
            }
            
            processed_changes.append(processed_change)
            
        return processed_changes

    def analyze_file_type(self, file_path: str, diff_content: str = '') -> Dict:
        """Enhanced file type analysis with framework detection"""
        file_info = {
            'type': 'unknown',
            'category': 'other',
            'frameworks': []
        }
        
        # Get file extension
        file_ext = '.' + file_path.split('.')[-1] if '.' in file_path else ''
        file_name = file_path.split('/')[-1].lower()
        
        # Determine primary file type
        for file_type, extensions in SUPPORTED_FILE_EXTENSIONS.items():
            if file_ext.lower() in extensions:
                file_info['type'] = file_type
                break
        
        # Special handling for Java files - check if Spring Boot
        if file_info['type'] == 'java' or file_ext == '.java':
            if self.is_spring_boot_file(file_path, diff_content):
                file_info['type'] = 'spring'
                file_info['frameworks'].append('Spring Boot')
        
        # Enhanced React detection
        if file_ext.lower() in ['.jsx', '.tsx'] or self.is_react_file(file_path, diff_content):
            file_info['frameworks'].append('React')
            if 'react' not in file_info['type']:
                file_info['type'] = 'react'
        
        # Determine category
        file_info['category'] = self.categorize_file(file_path, file_info['type'])
        
        return file_info

    def is_spring_boot_file(self, file_path: str, diff_content: str) -> bool:
        """Check if a Java file is Spring Boot related"""
        # Check file path patterns
        spring_path_indicators = [
            '/controller/', '/service/', '/repository/', '/config/',
            '/entity/', '/dto/', '/model/', 'Application.java'
        ]
        
        for indicator in spring_path_indicators:
            if indicator in file_path:
                return True
        
        # Check diff content for Spring annotations
        if diff_content:
            for pattern in SPRING_BOOT_PATTERNS:
                if re.search(pattern, diff_content, re.IGNORECASE):
                    return True
        
        return False

    def is_react_file(self, file_path: str, diff_content: str) -> bool:
        """Check if a file is React related"""
        # Check file path patterns
        react_path_indicators = [
            '/components/', '/pages/', '/hooks/', '/context/'
        ]
        
        for indicator in react_path_indicators:
            if indicator in file_path:
                return True
        
        # Check diff content for React patterns
        if diff_content:
            for pattern in REACT_PATTERNS:
                if re.search(pattern, diff_content, re.IGNORECASE):
                    return True
        
        return False

    def categorize_file(self, file_path: str, file_type: str) -> str:
        """Categorize files into logical groups"""
        file_path_lower = file_path.lower()
        
        # Test files
        if any(test_indicator in file_path_lower for test_indicator in ['test', 'spec', '__tests__']):
            return 'test'
        
        # Configuration files
        if file_type == 'config' or any(config_indicator in file_path_lower for config_indicator in ['config', 'properties', 'yml', 'yaml']):
            return 'configuration'
        
        # Documentation
        if any(doc_indicator in file_path_lower for doc_indicator in ['readme', 'doc', 'docs', '.md']):
            return 'documentation'
        
        # Frontend
        if file_type in ['react', 'frontend', 'javascript']:
            return 'frontend'
        
        # Backend
        if file_type in ['java', 'spring']:
            return 'backend'
        
        return 'other'

    def determine_change_type(self, change: Dict) -> str:
        """Determine the type of change made to a file"""
        if change.get('new_file', False):
            return 'added'
        elif change.get('deleted_file', False):
            return 'deleted'
        elif change.get('renamed_file', False):
            return 'renamed'
        else:
            return 'modified'

    def send_to_gemini_analysis(self, mr_data: Dict, changes: List[Dict]) -> str:
        """Send MR data to Gemini for enhanced analysis"""
        try:
            if not self.gemini_ready:
                logger.warning("Gemini interface not ready, using fallback analysis")
                return self.generate_fallback_analysis(mr_data, changes)

            # Switch to Gemini tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Prepare enhanced prompt
            prompt = self.create_enhanced_analysis_prompt(mr_data, changes)
            
            # Find input area and send prompt
            input_selectors = [
                "[data-test-id='input-area']",
                "div[contenteditable='true']",
                "[role='textbox']",
                ".ProseMirror"
            ]
            
            input_element = None
            for selector in input_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    input_element = elements[0]
                    break
            
            if not input_element:
                logger.warning("Could not find Gemini input element")
                return self.generate_fallback_analysis(mr_data, changes)
            
            # Clear any existing content and send prompt
            input_element.click()
            time.sleep(1)
            
            # Use JavaScript to set content for better reliability
            self.driver.execute_script("arguments[0].innerHTML = arguments[1];", input_element, prompt)
            time.sleep(2)
            
            # Send the message
            input_element.send_keys(Keys.RETURN)
            
            # Wait for response
            logger.info("Waiting for Gemini response...")
            time.sleep(10)
            
            # Try to extract the response
            response = self.extract_gemini_response()
            
            if response and len(response.strip()) > 100:
                logger.info("✅ Successfully received Gemini analysis")
                return response
            else:
                logger.warning("Gemini response was too short or empty, using fallback")
                return self.generate_fallback_analysis(mr_data, changes)
                
        except Exception as e:
            logger.error(f"Error with Gemini analysis: {e}")
            return self.generate_fallback_analysis(mr_data, changes)

    def create_enhanced_analysis_prompt(self, mr_data: Dict, changes: List[Dict]) -> str:
        """Create an enhanced prompt for Gemini analysis"""
        
        # Categorize changes by type and framework
        change_summary = self.summarize_changes(changes)
        
        prompt = f"""
Please analyze this GitLab Merge Request and provide comprehensive technical documentation:

**Merge Request Information:**
- Title: {mr_data.get('title', 'N/A')}
- Description: {mr_data.get('description', 'No description provided')[:500]}...
- Author: {mr_data.get('author', {}).get('name', 'Unknown')}
- Target Branch: {mr_data.get('target_branch', 'Unknown')}
- Source Branch: {mr_data.get('source_branch', 'Unknown')}

**Change Summary:**
{change_summary}

**Analysis Requirements:**
1. **Executive Summary**: Brief overview of what this MR accomplishes
2. **Technical Impact**: Key technical changes and their implications
3. **Architecture Changes**: Any architectural or design pattern changes
4. **Dependencies**: New dependencies or integrations introduced
5. **Testing Strategy**: Recommended testing approach for these changes
6. **Deployment Considerations**: Important notes for deployment
7. **Risk Assessment**: Potential risks and mitigation strategies
8. **Code Quality**: Overall code quality assessment

Please provide detailed, professional documentation suitable for technical stakeholders.
"""
        
        return prompt.strip()

    def summarize_changes(self, changes: List[Dict]) -> str:
        """Create a summary of changes by category"""
        summary_parts = []
        
        # Group by category
        categories = {}
        for change in changes:
            category = change['file_category']
            if category not in categories:
                categories[category] = []
            categories[category].append(change)
        
        # Create summary for each category
        for category, category_changes in categories.items():
            change_types = {}
            frameworks = set()
            
            for change in category_changes:
                change_type = change['change_type']
                change_types[change_type] = change_types.get(change_type, 0) + 1
                frameworks.update(change['frameworks'])
            
            framework_info = f" (Frameworks: {', '.join(frameworks)})" if frameworks else ""
            change_details = ", ".join([f"{count} {change_type}" for change_type, count in change_types.items()])
            
            summary_parts.append(f"- **{category.title()}**: {change_details}{framework_info}")
        
        return "\n".join(summary_parts) if summary_parts else "No categorized changes found"

    def extract_gemini_response(self) -> str:
        """Extract response from Gemini interface"""
        try:
            # Wait a bit more for content to load
            time.sleep(5)
            
            # Try multiple selectors for response content
            response_selectors = [
                ".response-container",
                ".message-content",
                "[data-test-id='response']",
                ".chat-message",
                ".model-response"
            ]
            
            for selector in response_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Get the last (most recent) response
                    response_text = elements[-1].text.strip()
                    if len(response_text) > 50:  # Reasonable response length
                        return response_text
            
            # Fallback: get all text from body and try to extract response
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for response patterns (this is quite basic)
            lines = page_text.split('\n')
            response_lines = []
            capturing = False
            
            for line in lines:
                line = line.strip()
                if any(keyword in line.lower() for keyword in ['executive summary', 'technical impact', 'analysis']):
                    capturing = True
                if capturing and line:
                    response_lines.append(line)
                # Stop if we hit obvious UI elements
                if capturing and any(ui_element in line.lower() for ui_element in ['send message', 'new chat', 'clear']):
                    break
            
            if response_lines and len('\n'.join(response_lines)) > 100:
                return '\n'.join(response_lines)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting Gemini response: {e}")
            return ""

    def generate_fallback_analysis(self, mr_data: Dict, changes: List[Dict]) -> str:
        """Generate fallback analysis when Gemini is not available"""
        
        change_summary = self.summarize_changes(changes)
        
        # Count changes by type
        total_files = len(changes)
        added_files = len([c for c in changes if c['change_type'] == 'added'])
        modified_files = len([c for c in changes if c['change_type'] == 'modified'])
        deleted_files = len([c for c in changes if c['change_type'] == 'deleted'])
        
        # Identify frameworks
        all_frameworks = set()
        for change in changes:
            all_frameworks.update(change['frameworks'])
        
        analysis = f"""
# Technical Analysis: {mr_data.get('title', 'Merge Request')}

## Executive Summary
This merge request contains {total_files} file changes affecting multiple components of the application.

## Change Overview
- **Files Added**: {added_files}
- **Files Modified**: {modified_files}
- **Files Deleted**: {deleted_files}
- **Frameworks/Technologies**: {', '.join(all_frameworks) if all_frameworks else 'Standard technologies'}

## File Changes by Category
{change_summary}

## Technical Impact
Based on the file changes, this merge request appears to involve:
"""

        # Add specific insights based on file types
        categories = set(change['file_category'] for change in changes)
        
        if 'backend' in categories:
            analysis += "\n- **Backend Changes**: Server-side logic modifications"
        if 'frontend' in categories:
            analysis += "\n- **Frontend Changes**: User interface and client-side updates"
        if 'configuration' in categories:
            analysis += "\n- **Configuration Changes**: System configuration updates"
        if 'test' in categories:
            analysis += "\n- **Test Changes**: Test suite modifications"
        
        analysis += f"""

## Deployment Considerations
- Review all configuration changes before deployment
- Ensure proper testing of modified components
- Consider database migration requirements if applicable

## Recommended Testing
- Unit tests for modified business logic
- Integration tests for API changes
- UI testing for frontend modifications
- End-to-end testing for critical user workflows

---
*Analysis generated automatically. Please review code changes for complete understanding.*
"""
        
        return analysis.strip()

    def generate_documentation(self, merge_requests: List[Dict]) -> str:
        """Generate comprehensive documentation for multiple merge requests"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        documentation = f"""# GitLab Merge Request Documentation
Generated on: {timestamp}

## Summary
This document contains detailed analysis of {len(merge_requests)} merge request(s).

"""
        
        for i, mr_data in enumerate(merge_requests, 1):
            logger.info(f"Generating documentation for MR {i}/{len(merge_requests)}")
            
            # Get changes for this MR
            changes = self.get_merge_request_changes(
                mr_data['project_id'], 
                mr_data['mr_iid']
            )
            
            # Get enhanced analysis
            analysis = self.send_to_gemini_analysis(mr_data.get('mr_info', {}), changes)
            
            documentation += f"""
---

## Merge Request {i}: {mr_data.get('mr_info', {}).get('title', 'Unknown Title')}

**Project**: {mr_data['project_id']}  
**MR ID**: {mr_data['mr_iid']}  
**URL**: {mr_data.get('mr_info', {}).get('web_url', 'N/A')}

{analysis}

### Detailed File Changes

"""
            
            # Add detailed file listing
            if changes:
                for change in changes:
                    documentation += f"""
#### {change['file_path']}
- **Type**: {change['file_type']} ({change['file_category']})
- **Change**: {change['change_type']}
- **Frameworks**: {', '.join(change['frameworks']) if change['frameworks'] else 'None'}

"""
            else:
                documentation += "No detailed file changes available.\n\n"
        
        return documentation

    def save_documentation(self, documentation: str) -> str:
        """Save documentation to file"""
        
        if OUTPUT_FILENAME:
            filename = OUTPUT_FILENAME
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gitlab_mr_documentation_{timestamp}.md"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(documentation)
            
            logger.info(f"✅ Documentation saved to: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
            return ""

    def process_merge_requests(self) -> str:
        """Main method to process all merge requests"""
        
        logger.info(f"🚀 Starting processing of {len(MERGE_REQUESTS)} merge request(s)")
        
        accessible_mrs = []
        
        # Check accessibility of all MRs first
        for mr_config in MERGE_REQUESTS:
            project_id = mr_config['project_id']
            mr_iid = mr_config['mr_iid']
            
            logger.info(f"Checking accessibility of MR {project_id}/{mr_iid}")
            
            access_result = self.check_mr_accessibility(project_id, mr_iid)
            
            if access_result['accessible']:
                accessible_mrs.append({
                    'project_id': project_id,
                    'mr_iid': mr_iid,
                    'mr_info': access_result['mr_info'],
                    'access_method': 'api' if access_result['api_accessible'] else 'browser'
                })
            else:
                logger.error(f"❌ MR {project_id}/{mr_iid} is not accessible: {access_result.get('error', 'Unknown error')}")
        
        if not accessible_mrs:
            logger.error("❌ No merge requests are accessible. Please check your configuration.")
            return ""
        
        logger.info(f"✅ Found {len(accessible_mrs)} accessible merge request(s)")
        
        # Generate documentation
        documentation = self.generate_documentation(accessible_mrs)
        
        # Save documentation
        filename = self.save_documentation(documentation)
        
        if filename:
            logger.info(f"🎉 Documentation generation completed successfully!")
            logger.info(f"📄 Output file: {filename}")
        else:
            logger.error("❌ Failed to save documentation")
        
        return filename

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                logger.info("Browser driver closed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


def main():
    """Main function to run the MR documentation generator"""
    
    logger.info("="*60)
    logger.info("GitLab Merge Request Documentation Generator")
    logger.info("="*60)
    
    # Validate configuration
    if not GITLAB_URL or GITLAB_URL == "https://your-verizon-gitlab.com":
        logger.error("❌ Please configure GITLAB_URL in the script")
        return
    
    if not PRIVATE_TOKEN or PRIVATE_TOKEN == "your_private_token_here":
        logger.error("❌ Please configure PRIVATE_TOKEN in the script")
        return
    
    if not MERGE_REQUESTS:
        logger.error("❌ Please configure MERGE_REQUESTS in the script")
        return
    
    generator = None
    
    try:
        # Initialize generator
        generator = GitLabMRDocumentationGenerator(GITLAB_URL, PRIVATE_TOKEN)
        
        # Process merge requests
        output_file = generator.process_merge_requests()
        
        if output_file:
            logger.info(f"✅ Success! Documentation saved to: {output_file}")
        else:
            logger.error("❌ Documentation generation failed")
    
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        if generator:
            generator.cleanup()


if __name__ == "__main__":
    main()