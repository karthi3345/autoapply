# AutoApply AI - Multi-Platform Job Application Engine

Automate real job applications across **LinkedIn Easy Apply**, **Naukri**, and **Indeed** using AI and Playwright browser automation.

## Features
- **Modern Web Dashboard**: Real-time WebSocket activity logs, resume skill extraction, and application tracker.
- **AI Profile Parser**: Extracts skills and details from your uploaded PDF resume.
- **Persistent Browser Context**: Keeps you logged in safely across LinkedIn and Naukri sessions without triggering security blocks.
- **Direct Real Submissions**: Automates the multi-step "Easy Apply" dialog, attaches resumes, and submits applications directly.

## Quickstart

1. Install dependencies:
   ```bash
   pip install fastapi uvicorn pydantic python-multipart pypdf playwright aiofiles
   playwright install chromium
   ```

2. Start the server:
   ```bash
   uvicorn app:app --host 127.0.0.1 --port 8000 --reload
   ```

3. Open your browser:
   Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)
