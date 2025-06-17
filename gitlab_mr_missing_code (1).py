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
            if len(modified_files) > 10:
                summary.append(f"- ... and {len(modified_files) - 10} more modified files")
        
        return '\n'.join(summary) if summary else "No change details available"
    
    def _generate_file_analysis(self, changes: List[Dict]) -> str:
        """Generate file type analysis"""
        if not changes:
            return "No file analysis available"
        
        file_types = {}
        for change in changes:
            file_path = change.get('file', '')
            if not file_path:
                continue
            
            # Get file extension
            extension = Path(file_path).suffix.lower()
            if not extension:
                extension = 'no extension'
            
            if extension not in file_types:
                file_types[extension] = {'count': 0, 'additions': 0, 'deletions': 0}
            
            file_types[extension]['count'] += 1
            file_types[extension]['additions'] += change.get('additions', 0)
            file_types[extension]['deletions'] += change.get('deletions', 0)
        
        # Sort by count
        sorted_types = sorted(file_types.items(), key=lambda x: x[1]['count'], reverse=True)
        
        analysis = []
        for ext, stats in sorted_types:
            total_changes = stats['additions'] + stats['deletions']
            analysis.append(f"- **{ext}**: {stats['count']} files (+{stats['additions']}/-{stats['deletions']}) {total_changes} total changes")
        
        return '\n'.join(analysis) if analysis else "No file type analysis available"
    
    def _generate_commit_summary(self, commits: List[Dict]) -> str:
        """Generate commit summary"""
        if not commits:
            return "No commits available"
        
        summary = []
        for commit in commits:
            short_id = commit.get('short_id', 'unknown')
            title = commit.get('title', 'No title')
            author = commit.get('author_name', 'Unknown')
            date = commit.get('authored_date', '')[:10] if commit.get('authored_date') else 'Unknown date'
            
            summary.append(f"- **{short_id}**: {title} - *{author}* ({date})")
        
        return '\n'.join(summary)
    
    def _generate_impact_assessment(self, mr_data: MRData) -> str:
        """Generate impact assessment based on MR data"""
        impact = []
        
        # Size impact
        total_changes = mr_data.additions + mr_data.deletions
        if total_changes > 1000:
            impact.append("🔴 **High Impact**: Large code changes (>1000 lines)")
        elif total_changes > 500:
            impact.append("🟡 **Medium Impact**: Moderate code changes (500-1000 lines)")
        else:
            impact.append("🟢 **Low Impact**: Small code changes (<500 lines)")
        
        # File count impact
        if len(mr_data.files_changed) > 50:
            impact.append("🔴 **High File Impact**: Many files affected (>50)")
        elif len(mr_data.files_changed) > 20:
            impact.append("🟡 **Medium File Impact**: Multiple files affected (20-50)")
        else:
            impact.append("🟢 **Low File Impact**: Few files affected (<20)")
        
        # Project type specific impacts
        if mr_data.project_type == 'react':
            impact.append("📱 **Frontend Impact**: React application changes")
        elif mr_data.project_type == 'spring-boot':
            impact.append("⚙️ **Backend Impact**: Spring Boot application changes")
        elif mr_data.project_type == 'mixed':
            impact.append("🔄 **Full Stack Impact**: Both frontend and backend changes")
        
        # Pipeline status impact
        if mr_data.pipeline_status == 'failed':
            impact.append("❌ **Pipeline Risk**: Failed pipeline requires attention")
        elif mr_data.pipeline_status == 'success':
            impact.append("✅ **Pipeline Status**: All checks passed")
        
        return '\n'.join(impact) if impact else "No impact assessment available"
    
    def cleanup(self):
        """Cleanup WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

class DocumentationGenerator:
    """Main class for generating MR documentation"""
    
    def __init__(self, gitlab_url: str, private_token: str, use_gemini: bool = True, headless: bool = True):
        self.gitlab_client = GitLabAPIClient(gitlab_url, private_token)
        self.gemini_integration = GeminiProIntegration(headless=headless) if use_gemini else None
    
    def generate_documentation(self, mr_url: str, output_file: Optional[str] = None, use_gemini: bool = True) -> str:
        """Generate comprehensive documentation for a GitLab MR"""
        logger.info(f"Starting documentation generation for: {mr_url}")
        
        # Parse MR URL
        parsed = self.gitlab_client.parse_mr_url(mr_url)
        if not parsed:
            raise ValueError(f"Could not parse MR URL: {mr_url}")
        
        project_id, mr_iid = parsed
        logger.info(f"Processing MR !{mr_iid} from project {project_id}")
        
        # Fetch MR data
        mr_data = self.gitlab_client.get_mr_data(project_id, mr_iid)
        if not mr_data:
            raise ValueError(f"Could not fetch MR data for !{mr_iid}")
        
        logger.info(f"Successfully fetched MR data: {mr_data.title}")
        
        # Generate documentation
        if use_gemini and self.gemini_integration:
            logger.info("Generating documentation with Gemini Pro enhancement...")
            documentation = self.gemini_integration.enhance_documentation(mr_data)
        else:
            logger.info("Generating enhanced documentation without Gemini...")
            documentation = self.gemini_integration._generate_enhanced_documentation(mr_data) if self.gemini_integration else self._generate_basic_documentation(mr_data)
        
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(documentation)
            
            logger.info(f"Documentation saved to: {output_path}")
        
        return documentation
    
    def _generate_basic_documentation(self, mr_data: MRData) -> str:
        """Generate basic documentation without Gemini integration"""
        return f"""# {mr_data.title}

## Basic Information
- **MR ID**: !{mr_data.iid}
- **Author**: {mr_data.author}
- **Project**: {mr_data.project_name}
- **Status**: {mr_data.state}
- **Created**: {mr_data.created_at}

## Description
{mr_data.description or 'No description provided'}

## Changes Summary
- Files changed: {len(mr_data.files_changed)}
- Lines added: {mr_data.additions}
- Lines deleted: {mr_data.deletions}
- Commits: {len(mr_data.commits)}

## Files Changed
{chr(10).join(f'- {file}' for file in mr_data.files_changed)}

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    def cleanup(self):
        """Cleanup resources"""
        if self.gemini_integration:
            self.gemini_integration.cleanup()

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Generate technical documentation from GitLab Merge Requests')
    parser.add_argument('mr_url', help='GitLab MR URL')
    parser.add_argument('--gitlab-url', required=True, help='GitLab instance URL')
    parser.add_argument('--token', required=True, help='GitLab private token')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--no-gemini', action='store_true', help='Disable Gemini Pro integration')
    parser.add_argument('--no-headless', action='store_true', help='Run browser in non-headless mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize documentation generator
        doc_generator = DocumentationGenerator(
            gitlab_url=args.gitlab_url,
            private_token=args.token,
            use_gemini=not args.no_gemini,
            headless=not args.no_headless
        )
        
        # Generate documentation
        documentation = doc_generator.generate_documentation(
            mr_url=args.mr_url,
            output_file=args.output,
            use_gemini=not args.no_gemini
        )
        
        # Print to console if no output file specified
        if not args.output:
            print(documentation)
        
        logger.info("Documentation generation completed successfully")
        
    except Exception as e:
        logger.error(f"Error generating documentation: {e}")
        raise
    finally:
        # Cleanup
        if 'doc_generator' in locals():
            doc_generator.cleanup()

if __name__ == "__main__":
    main()