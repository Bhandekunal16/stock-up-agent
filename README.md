# Portfolio Signals API

A Python-based Flask API that executes a portfolio signal generation script and returns its execution results in JSON format.

The API acts as a wrapper around `runner.sh`, which executes the portfolio signals processing logic using Python.

## Features

- Flask-based REST API.
- Executes portfolio signal generation through a shell script.
- Supports MongoDB connectivity through environment variables.
- Returns structured JSON responses.
- Captures standard output and error output.
- Includes execution timeout handling.
- Supports deployment on Vercel.

## Tech Stack

- **Python** – Core application and signal processing.
- **Flask** – REST API framework.
- **PyMongo** – MongoDB connectivity.
- **Bash** – Script execution.
- **Vercel** – Serverless deployment.

## Project Structure

```text
.
├── app.py
├── portfolio_signals.py
├── algorithm.py
├── runner.sh
├── installer.sh
├── requirements.txt
├── vercel.json
├── README.md
└── api.md
```

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Configure the MongoDB connection string:

```env
MONGODB_URI=your_mongodb_connection_string
```

Do not commit database credentials to the repository.

### 5. Run Application

```bash
python3 app.py
```

The application starts on:

```text
http://localhost:5001
```

## API Endpoint

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/portfolio/signals` | Executes portfolio signal generation |

See [api.md](api.md) for complete API documentation.

## Execution Flow

1. Client sends a GET request.
2. Flask receives the request.
3. Flask executes `runner.sh` using subprocess.
4. The shell script executes `portfolio_signals.py`.
5. The Python script processes portfolio signals.
6. Flask captures the execution output.
7. The API returns the result as JSON.

## Deployment

The application can be deployed on Vercel using the Python runtime.

Ensure:
- `requirements.txt` is included in the deployment.
- `runner.sh` is included and executable or invoked through Bash.
- All required Python modules are included.
- MongoDB connection details are configured as Vercel environment variables.
- All scripts and required files are included in the deployment.

## Dependencies

Example `requirements.txt`:

```text
Flask==3.1.0
pymongo[srv]
```

Add any additional external packages used by the algorithm.

## Error Handling

| HTTP Status | Description |
|---|---|
| 200 | Script executed successfully |
| 500 | Script execution failed or unexpected error |
| 504 | Script execution timed out |

## Security Notes

- Store MongoDB credentials in environment variables.
- Never expose database credentials in source code.
- Avoid exposing sensitive information through error responses.
- Consider authentication and rate limiting before making the endpoint publicly accessible.

## License

Specify your project's license here.