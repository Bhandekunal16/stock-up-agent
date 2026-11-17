# Portfolio Signals API Documentation

## Overview

The Portfolio Signals API provides an endpoint to execute portfolio signal generation and retrieve the execution result.

The API uses Flask to execute `runner.sh`, which internally runs the Python portfolio signals processing script.

## Base URL

Local:

```text
http://localhost:5001
```

Production:

```text
https://your-vercel-domain.vercel.app
```

## Endpoint

### Generate Portfolio Signals

Executes the portfolio signal generation script.

**Request**

```http
GET /api/portfolio/signals
```

**Full URL (Local)**

```text
http://localhost:5001/api/portfolio/signals
```

**Method:** `GET`

**Authentication:** Not implemented in the current code.

**Request Parameters:** None.

**Request Body:** None.

### Request Example

```bash
curl -X GET \
  http://localhost:5001/api/portfolio/signals
```

Production:

```bash
curl -X GET \
  https://your-vercel-domain.vercel.app/api/portfolio/signals
```

## Execution Process

When the endpoint is called:

1. Executes `runner.sh` through Bash.
2. Captures standard output (`stdout`).
3. Captures standard error (`stderr`).
4. Waits for script completion.
5. Terminates execution if it exceeds 120 seconds.
6. Returns the execution result as JSON.

## Success Response

**HTTP Status:** `200 OK`

```json
{
  "success": true,
  "exitCode": 0,
  "output": "Portfolio signals generated successfully",
  "error": ""
}
```

| Field | Type | Description |
|---|---|---|
| success | Boolean | Indicates whether execution succeeded |
| exitCode | Integer | Process exit code; 0 indicates success |
| output | String | Standard output from the script |
| error | String | Standard error from the script |

The output shown above is illustrative. Actual output depends on `portfolio_signals.py`.

## Error Responses

### 1. Script Execution Failure

**HTTP Status:** `500 Internal Server Error`

```json
{
  "success": false,
  "exitCode": 1,
  "output": "",
  "error": "Script execution failed"
}
```

Returned when the shell script or Python process exits with a non-zero status.

### 2. Execution Timeout

**HTTP Status:** `504 Gateway Timeout`

```json
{
  "success": false,
  "message": "Script execution timed out"
}
```

Returned when script execution exceeds 120 seconds.

### 3. Unexpected Application Error

**HTTP Status:** `500 Internal Server Error`

```json
{
  "success": false,
  "message": "Failed to execute portfolio signals"
}
```

Returned when an unexpected exception occurs while executing the request.

## Configuration

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| MONGODB_URI | If required by the script | MongoDB connection string |

Configure environment variables in Vercel:

1. Open Vercel Dashboard.
2. Select your project.
3. Navigate to Settings → Environment Variables.
4. Add `MONGODB_URI`.
5. Redeploy the application.

## Dependencies

Example `requirements.txt`:

```text
Flask==3.1.0
pymongo[srv]
```

## Script Configuration

The API executes:

```bash
bash runner.sh
```

The shell script is responsible for starting the portfolio signal processing logic.

Expected execution chain:

```text
API Request
    |
    v
Flask Endpoint
    |
    v
runner.sh
    |
    v
portfolio_signals.py
    |
    v
MongoDB / Portfolio Processing
    |
    v
Execution Result
    |
    v
JSON Response
```

## Timeout Configuration

Current subprocess timeout:

```python
timeout=120
```

Maximum script execution time configured by the application is 120 seconds, subject to the deployment platform's own execution limits.

## Important Notes

- The endpoint currently uses GET to trigger script execution.
- No authentication or authorization is implemented.
- Every request executes the script again.
- The API does not independently guarantee that signals are stored or updated; that depends on the Python processing script.
- Avoid simultaneous requests if the underlying script modifies shared portfolio data.
- Vercel serverless execution limits may restrict long-running jobs.

## Future Improvements

- Add API authentication.
- Add request logging.
- Add execution IDs and status tracking.
- Add background job processing for long-running algorithms.
- Add structured signal results instead of returning only console output.
- Add rate limiting to prevent repeated executions.