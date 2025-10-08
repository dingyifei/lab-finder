# Test Data Directory

This directory contains example/template files for local testing of the Lab Finder application.

## Setup Instructions

1. **Copy your resume:**
   ```bash
   cp /path/to/your/resume.pdf test_data/resume.pdf
   ```

2. **The application expects:**
   - `test_data/resume.pdf` - Your actual resume (git-ignored)
   - This file will be used by the profile consolidation agent

## Files

- `resume.example.pdf` - Example resume template (committed to repo)
- `resume.pdf` - Your actual resume (git-ignored, you create this)

## Note

Never commit your actual resume (`resume.pdf`) to the repository. The `.gitignore` file ensures it stays local.
