}, indent=2)
        
        logger.info(f"Summary report saved: {summary_path}")
        logger.info(f"Raw data saved: {data_path}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.gemini:
            self.gemini.close()

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Generate technical documentation from GitLab Merge Requests')
    parser.add_argument('--gitlab-url', required=True, help='GitLab instance URL (e.g., https://gitlab.com)')
    parser.add_argument('--token', required=True, help='GitLab private access token')
    parser.add_argument('--mr-urls', nargs='+', help='List of MR URLs to process')
    parser.add_argument('--mr-file', help='File containing MR URLs (one per line)')
    parser.add_argument('--output-dir', default='documentation', help='Output directory for documentation')
    parser.add_argument('--no-gemini', action='store_true', help='Disable Gemini Pro integration')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Collect MR URLs
    mr_urls = []
    
    if args.mr_urls:
        mr_urls.extend(args.mr_urls)
    
    if args.mr_file:
        try:
            with open(args.mr_file, 'r', encoding='utf-8') as f:
                file_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                mr_urls.extend(file_urls)
        except FileNotFoundError:
            logger.error(f"MR file not found: {args.mr_file}")
            return 1
        except Exception as e:
            logger.error(f"Error reading MR file: {e}")
            return 1
    
    if not mr_urls:
        logger.error("No MR URLs provided. Use --mr-urls or --mr-file")
        return 1
    
    # Remove duplicates while preserving order
    mr_urls = list(dict.fromkeys(mr_urls))
    
    logger.info(f"Found {len(mr_urls)} unique MR URLs to process")
    
    # Validate GitLab token
    if not args.token or len(args.token) < 10:
        logger.error("Invalid GitLab token. Please provide a valid private access token")
        return 1
    
    # Initialize documentation generator
    try:
        doc_generator = DocumentationGenerator(
            gitlab_url=args.gitlab_url,
            private_token=args.token,
            use_gemini=not args.no_gemini,
            headless=args.headless
        )
        
        # Process MRs
        doc_generator.process_mr_list(mr_urls, args.output_dir)
        
        # Print summary
        success_count = len(doc_generator.processed_mrs)
        failed_count = len(doc_generator.failed_mrs)
        
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Successfully processed: {success_count} MRs")
        print(f"❌ Failed to process: {failed_count} MRs")
        print(f"📁 Documentation saved in: {args.output_dir}/")
        print(f"📊 Summary report: {args.output_dir}/README.md")
        
        if failed_count > 0:
            print(f"\nFailed MRs:")
            for failed in doc_generator.failed_mrs:
                print(f"  - {failed['url']}: {failed['reason']}")
        
        return 0 if failed_count == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        # Cleanup
        if 'doc_generator' in locals():
            doc_generator.cleanup()

def create_sample_config():
    """Create a sample configuration file"""
    config = {
        "gitlab_url": "https://gitlab.com",
        "private_token": "your-gitlab-private-token-here",
        "output_directory": "documentation",
        "use_gemini": True,
        "headless_browser": True,
        "mr_urls": [
            "https://gitlab.com/your-group/your-project/-/merge_requests/123",
            "https://gitlab.com/your-group/your-project/-/merge_requests/124"
        ]
    }
    
    config_path = "config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"Sample configuration created: {config_path}")
    print("Edit the file with your GitLab URL, token, and MR URLs")

def validate_environment():
    """Validate that required dependencies are available"""
    required_packages = [
        'requests', 'pandas', 'selenium'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    # Check for Chrome/Chromium
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        driver = webdriver.Chrome(options=chrome_options)
        driver.quit()
    except Exception as e:
        print("Chrome/Chromium not found or not properly configured.")
        print("Please ensure Chrome/Chromium and ChromeDriver are installed.")
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    
    # Special commands
    if len(sys.argv) > 1:
        if sys.argv[1] == 'create-config':
            create_sample_config()
            sys.exit(0)
        elif sys.argv[1] == 'validate':
            if validate_environment():
                print("✅ Environment validation passed")
                sys.exit(0)
            else:
                print("❌ Environment validation failed")
                sys.exit(1)
    
    # Run main application
    sys.exit(main())