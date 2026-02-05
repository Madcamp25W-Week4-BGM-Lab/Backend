# SubText Backend

The SubText Backend is a FastAPI application designed to leverage Large Language Models (LLMs) for automated content generation, specifically for Git commit messages and project README files. It provides a robust, asynchronous task processing system for handling LLM-based generation requests.

## Features

### Commit Message Generation
- **Intelligent Commit Messages:** Generates Git commit messages based on code differences (diffs).
- **Customizable Styles:** Supports various commit conventions including `conventional`, `angular`, and `gitmoji`.
- **Formatting Options:** Configurable casing (e.g., `lowercase`, `sentence case`), maximum message length, and optional ticket prefixes (e.g., `PROJ-123`).
- **Multilingual Support:** Generates commit messages in specified languages.
- **Custom Rules:** Allows users to define custom rules to override standard conventions.

### README File Generation
- **Dynamic READMEs:** Generates comprehensive README files tailored to project facts (repository type, runtime environment, build scripts).
- **Audience-Specific Templates:** Utilizes predefined templates optimized for different target audiences: `developer`, `designer`, `general`, and `extension`.
- **Structured Content:** Ensures consistent and well-organized documentation based on the selected repository type (research, library, service).

### Asynchronous Task Processing
- **Task Queuing System:** Implements an internal task queue to handle LLM generation requests asynchronously.
- **Worker-Friendly API:** Provides API endpoints for external worker services (e.g., GPU servers) to fetch pending tasks and submit completed results.
- **Status Polling:** Clients can poll specific endpoints to check the status and retrieve the results of their generation tasks.

## Technology Stack
- **Framework:** FastAPI
- **Language:** Python
- **Dependency Management:** pydantic, pydantic-settings, python-dotenv
- **Asynchronous Operations:** Uvicorn, background task queue
- **Testing:** pytest, pytest-asyncio, httpx

## API Endpoints

### Health Check
- `GET /`
  - Returns the service status and links to documentation.

### Commit Message API
- `POST /api/v1/commits/`
  - Queues an asynchronous task for generating a commit message.
  - **Request Body:** `CommitRequest` (includes `diff`, `config`, `history`).
  - **Response:** `CommitTaskResponse` (contains `task_id` for polling).
- `GET /api/v1/commits/{task_id}`
  - Polls for the status and result of a commit generation task.
  - **Response:** `CommitPollResponse` (contains `status`, `commit_message` or `error`).

### README Generation API
- `POST /api/v1/readmes/`
  - Generates a README file, either synchronously or asynchronously.
  - **Request Body:** `ReadmeGenerateRequest` (includes `fact`, `mode`, `doc_target`, `async_mode`).
  - **Response (Synchronous):** `ReadmeGenerateResponse` (contains `content`, `template`).
  - **Response (Asynchronous):** `ReadmeGenerateResponse` (contains `task_id`, `template`).
- `GET /api/v1/readmes/{task_id}`
  - Polls for the status and result of a README generation task.
  - **Response:** `ReadmePollResponse` (contains `status`, `content` or `error`).

### Infrastructure API (For Workers)
- `POST /infrastructure/queue/pop`
  - Allows an external worker to retrieve a pending LLM task from the queue.
  - **Response:** `LLMTask` (details of the task to be processed).
- `POST /infrastructure/queue/complete/{task_id}`
  - Allows an external worker to mark a task as complete and submit its result.
  - **Request Body:** JSON payload with the `result`.
  - **Response:** `{"status": "ok"}`

## Setup and Installation

### Prerequisites
- Python 3.8+
- `pip` for package management

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/subtext-backend.git
   cd subtext-backend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the project root based on `src/config.py` for local development.

   ```ini
   APP_NAME="SubText Backend"
   ENVIRONMENT="local"
   API_KEY="your-secret-api-key" # IMPORTANT: Change this in production
   HOST="0.0.0.0"
   PORT=8000 # Or any desired port
   RELOAD=True
   ```

## Running the Application

To run the application locally:

```bash
python run.py
```

The API documentation will be available at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc) once the application is running.

## Development and Contributing

(Add sections for development guidelines, testing, and contribution instructions here.)

## License

(Add license information here.)
