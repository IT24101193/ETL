# Customer CSV ETL API

A small, containerized ETL service built with Django REST Framework. It accepts
customer records from a CSV upload, validates the complete file, then creates or
updates records in PostgreSQL. Imports are all-or-nothing: invalid rows do not
partially write data.

## Requirements

- Docker Desktop with Docker Compose
- Git (optional, for the workflow below)

## Run with Docker

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000`. Docker Compose starts PostgreSQL,
waits for its health check, applies database migrations, and starts the API.
To stop the services, press `Ctrl+C`; use `docker compose down` to remove
containers while keeping database data, or `docker compose down -v` to also
delete the database volume.

For anything beyond local development, set `DJANGO_SECRET_KEY` and
`POSTGRES_PASSWORD` to strong secret values through the environment; do not
commit secrets to the repository.

## CSV format

The first row must contain the required `name` and `email` columns. `phone` and
`company` are optional. Column names are case-sensitive; additional or duplicate
columns are rejected. Files must be UTF-8 (with or without a BOM), contain at
least one customer row, and be no larger than 10 MB.

```csv
name,email,phone,company
Ada Lovelace,ada@example.com,+1-555-0100,Analytical Engines
Grace Hopper,grace@example.com,+1-555-0101,US Navy
```

Emails are trimmed and lowercased. Re-importing an email updates that customer;
new emails create customers. Duplicate emails within one file and any invalid
row reject the entire import.

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health/` | Liveness check |
| `POST` | `/api/imports/customers/` | Import a CSV using multipart field `file` |
| `GET` | `/api/customers/` | List imported customers |

Example upload:

```powershell
curl.exe -X POST -F "file=@customers.csv" http://localhost:8000/api/imports/customers/
```

Successful import response:

```json
{"created": 2, "updated": 0, "total": 2}
```

## Local development and tests

Python 3.12+ is recommended. SQLite is used by default for local development and
tests; Docker Compose configures the application to use PostgreSQL.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
python manage.py test
```

The test suite uses Django's test runner and covers uploads, validation,
idempotent updates, and customer listing. `pytest` is available as an alternate
runner:

```powershell
pytest
```

## Git workflow

Start development on `develop` and merge completed work into `main`:

```powershell
git init
git switch -c main
git switch -c develop
# Make and test changes on develop
git add .
git commit -m "Build customer CSV ETL API"
git switch main
git merge --no-ff develop
```

If the repository is already initialized, keep its existing branches and apply
the same workflow without running `git init`.
