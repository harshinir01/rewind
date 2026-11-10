Rewind --- AI Agent Debugging & Verified Repair Platform
Rewind is a web application for inspecting AI-agent executions,
understanding why a run failed, and validating proposed fixes. The
project uses a React + TypeScript frontend and a Python FastAPI backend.

Project status: This README describes the current development
setup. Some screens or workflows may still use demo data or
placeholder behavior. A successful UI response does not, by itself,
prove that a real AI agent was executed. Verify each workflow against
the backend and database.

Features
The current interface includes areas for:

All Runs: Browse and inspect recorded agent runs.
Run Details: Review an individual run and its recorded execution
information.
Try a Fix: Explore a proposed fix workflow.
Batch Verification: Test or compare multiple runs.
API Contracts: Inspect the backend connection and API
information.
Dashboard analytics: View run counts, outcomes, execution costs,
and other summary information when those values are supplied by the
backend.
Availability and completeness of each feature depend on the current
implementation and any configured agent integrations.

Technology Stack
Frontend: React, TypeScript, Vite
Backend: Python, FastAPI, Uvicorn
Database: SQLite with SQLAlchemy (as configured in the backend)
Development tools: VS Code, Node.js, npm, Python
Prerequisites
Install the following before running the project:

Python
Node.js and npm
Git (optional, for version control)
VS Code (recommended)
Project Structure
The project is organized approximately as follows:

rewind/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── ...                 # Backend application, routers, services and models
├── src/
│   ├── pages/
│   ├── api/
│   └── ...                 # React frontend source
├── package.json
├── .gitignore
└── README.md
Your actual folder structure may contain additional files or differ
slightly. Keep existing project files intact.

Setup and Run Locally
Run the backend and frontend in two separate VS Code terminals. Keep
both terminals open while using the application.

1. Open the project folder
cd C:\Users\Harshini\OneDrive\Documents\rewind
If your project is stored elsewhere, replace the path with your actual
project directory.

2. Set up and start the backend
Create a virtual environment if one does not already exist:

py -m venv .venv
Activate it in PowerShell:

.\.venv\Scripts\Activate.ps1
Install backend dependencies:

python -m pip install -r backend\requirements.txt
Start FastAPI from the project root:

python -m uvicorn backend.main:app --reload --port 8000
Backend URLs:

API base: http://localhost:8000
Interactive API documentation: http://localhost:8000/docs
If PowerShell blocks virtual-environment activation, use the Python
executable directly:

.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
3. Set up and start the frontend
Open a second terminal at the project root:

cd C:\Users\Harshini\OneDrive\Documents\rewind
Install frontend dependencies:

npm install
Start the development server:

npm run dev
Open the local URL printed by Vite in the terminal. The project has
previously been accessed at:

http://localhost:3000

If Vite prints a different port, use the URL it displays.

Example Test Query
Use the following query in the SQL Agent or execution interface,
provided that a sales dataset or database connection is configured:

Analyze the sales data for the last 30 days. Calculate total revenue, identify the top 5 products by sales, compare revenue across regions, and highlight any unusual changes. Return the results in a structured report with supporting data.
What to verify
The application accepts the query.
The backend receives the request.
The configured agent or execution service actually processes it.
The response is based on available sales data, not a hardcoded
sample response.
The run is recorded and can be found under All Runs.
The run details and logs are available after refreshing the page.
Errors are reported clearly if the database, dataset, or agent
integration is unavailable.
Note: This query requires access to sales records. If no sales
dataset is configured, use a query that matches the data source
available in your environment. Do not treat a fabricated response as a
successful database or agent test.

Testing Checklist
Backend starts without errors.
http://localhost:8000/docs loads.
Frontend starts and loads in the browser.
Frontend reports the correct backend connection status.
A test request reaches the backend.
Execution results are based on real processing.
Runs are persisted in the database.
Run details and logs load correctly.
Empty states and API errors are handled.
Demo data is clearly identified as demo data.
No secrets or local environment files are committed to Git.
Demo Data vs. Real Execution Data
Demo traces can help test the dashboard and user interface. They are not
proof of real agent execution.

Demo data: Sample records inserted for demonstration or testing.
Backend-persisted data: Records saved by the application in its
database. These may still be demo records.
Real execution data: Records produced by an actual configured
agent or execution service.
A genuine AI-agent workflow may require provider credentials,
environment variables, a configured model, and an execution integration.
Configure credentials locally using environment variables or an
untracked .env file. Never commit API keys, passwords, or tokens.

Troubleshooting
Backend command fails
Confirm that the terminal is in the project root.
Confirm that backend\requirements.txt exists.
Activate the correct virtual environment.
Read the first Python traceback error and resolve the missing
dependency or configuration.
Frontend cannot connect to the backend
Confirm that the backend is running on port 8000.
Check the frontend API base URL configuration.
Check the browser developer console and backend terminal for errors.
Confirm that CORS settings allow the frontend's local origin.
Port is already in use
Stop the previous development process or choose another available port,
then update the relevant frontend API configuration if necessary.

Results look identical every time
Check whether the UI is displaying hardcoded mock data, seeded demo
traces, cached responses, or actual backend responses. Inspect the
network request and backend logs before concluding that the agent is
working.

Git and GitHub
Initialize Git from the project root:

git init
git add .
git status
git commit -m "Initial commit - Rewind project"
Connect your GitHub repository (replace the URL with your own):

git remote add origin https://github.com/harshinir01/rewind.git
git branch -M main
git push -u origin main
Before committing, make sure .venv/, node_modules/, .env files,
local databases, and other generated or sensitive files are excluded
through .gitignore. Review git status before every commit.

Development Notes
Start the backend and frontend in separate terminals.
Keep credentials out of source control.
Label demo data clearly.
Do not report a repair or verification as successful unless the
backend actually performed and recorded it.
Update this README when setup commands, environment variables, or
project capabilities change.
