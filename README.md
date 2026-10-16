# AI Data Analyst & BI Automation Agent

An intelligent data analysis platform built with **FastAPI, React, Python, and SQLite**. This project helps users analyze datasets, assess data quality, detect anomalies, answer business questions, compare historical analysis results, and generate downloadable PDF reports.

## Features

- **Dataset Management:** Upload and manage datasets for analysis.
- **Data Quality Analysis:** Identify missing values, duplicate records, and potential data quality issues.
- **Anomaly Detection:** Detect unusual records and numerical outliers.
- **Business Question Analysis:** Answer supported analytical questions using dataset information.
- **Analysis Planner:** Plan suitable analysis steps based on user questions.
- **Agent Execution Engine:** Execute supported analysis tasks and return structured results.
- **Historical Intelligence:** Compare current results with previous analysis snapshots.
- **Interactive Dashboard:** Explore analytical results and visualizations.
- **PDF Report Generation:** Generate downloadable reports containing dataset analysis results.
- **Automated Testing:** Test backend functionality, API integration, analysis planning, execution, and report generation.

## Technology Stack

### Backend
- Python 3.12
- FastAPI
- SQLite
- Pandas
- NumPy
- Pytest

### Frontend
- React
- Vite
- Plotly
- ESLint

## Project Structure

```text
ai-data-analyst-agent/
├── backend/                 # Backend API and analysis logic
├── database/                # Local SQLite database
├── data/                    # Local datasets
├── frontend/                # React dashboard
│   ├── src/                 # Frontend source code
│   └── .env.example         # Example environment configuration
├── reports/                 # Generated PDF reports
├── tests/                   # Automated backend tests
├── requirements.txt         # Python dependencies
├── .gitignore               # Files excluded from version control
└── README.md                # Project documentation
```

## Installation

### 1. Backend Setup

Create and activate a Python virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required Python packages:

```powershell
python -m pip install -r requirements.txt
```

### 2. Frontend Setup

Open a terminal in the project root and run:

```powershell
cd frontend
npm install
```

## Running the Application

### Start the Backend

From the project root, activate the virtual environment and run:

```powershell
uvicorn backend.main:app --reload
```

Backend URL:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### Start the Frontend

Open a second terminal:

```powershell
cd frontend
npm run dev
```

Open the local URL displayed by Vite, usually:

`http://localhost:5173`

## Environment Configuration

The frontend supports a configurable backend URL through the `VITE_API_BASE_URL` environment variable.

Example:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Create a local `frontend/.env` file if needed. Restart the frontend development server after changing environment variables.

**Security:** Never put private API keys, passwords, or other secrets in frontend environment variables because Vite exposes `VITE_` variables to browser code.

## Running Tests

Run the complete backend test suite from the project root:

```powershell
python -m pytest -q
```

Run frontend lint checks:

```powershell
cd frontend
npm run lint
```

Create a production frontend build:

```powershell
npm run build
```

## PDF Report Generation

The backend provides a PDF report endpoint:

```text
GET /datasets/{dataset_id}/report/pdf
```

Replace `{dataset_id}` with the ID of an available dataset. The endpoint can be explored through the FastAPI documentation at `/docs`.

Generated reports should be reviewed before sharing because they may contain dataset information.

## Latest Test Results

The latest recorded verification showed:

- **Backend:** 363 tests passed.
- **Frontend lint:** Passed.
- **Frontend production build:** Passed.

Known improvement areas include reducing the frontend JavaScript bundle size and addressing dependency deprecation and numerical correlation warnings.

## Security and Deployment

Before deploying publicly:

- Configure CORS for the intended production frontend domain.
- Implement appropriate authentication and authorization.
- Validate uploaded files and impose resource limits.
- Protect private datasets, local databases, and generated reports.
- Keep credentials and environment files out of public repositories.
- Configure production hosting and environment variables.

The development server should not be used as a production deployment server.

## Future Improvements

- Optimize frontend bundle size through code splitting.
- Resolve outstanding warnings.
- Improve security and production configuration.
- Add automated CI checks.
- Complete deployment and end-to-end verification.
- Expand analysis capabilities and report customization.

## License

No license has been selected yet. Add an appropriate license before permitting others to reuse or distribute this project.

## Author
Muhammad Awais
Software engineering student