## 🔢 Module 12 – FastAPI User Authentication and Calculation API

## 🗂️ Project Overview

This project builds on the previous calculator API by adding user registration, login functionality, and full CRUD operations for calculations using FastAPI, SQLAlchemy, Pydantic, and PostgreSQL.

The application allows users to register and log in securely, create calculations, retrieve saved calculations, update existing calculations, and delete calculations. It also includes automated integration tests and a CI/CD pipeline using GitHub Actions to test the application and publish a Docker image to Docker Hub.

## 💻 Technologies Used

- **Python** – Main programming language
- **FastAPI** – API framework
- **SQLAlchemy** – Database models and operations
- **Pydantic** – Request validation and response schemas
- **PostgreSQL** – Relational database
- **Pytest** – Automated testing
- **Docker and Docker Compose** – Containerization and application deployment
- **GitHub Actions** – Automated testing and CI/CD
- **Docker Hub** – Container image repository


## 🧩 Features

### 1. User Endpoints

The application includes user registration and login functionality.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/users/register` | Registers a new user |
| POST | `/users/login` | Verifies user login credentials |

User passwords are hashed before being stored in the database. The login endpoint verifies the submitted password against the stored password hash. Pydantic schemas are used to validate user input and structure responses.

### 2. Calculation Endpoints (BREAD)

The application implements all five BREAD operations:

| Operation | Method | Endpoint | Description |
|---|---|---|---|
| Browse | GET | `/calculations` | Retrieves calculations |
| Read | GET | `/calculations/{calculation_id}` | Retrieves a specific calculation |
| Edit | PUT | `/calculations/{calculation_id}` | Updates an existing calculation |
| Add | POST | `/calculations` | Creates a new calculation |
| Delete | DELETE | `/calculations/{calculation_id}` | Deletes a calculation |

The calculation endpoints use the existing `Calculation` SQLAlchemy model and the `CalculationCreate` and `CalculationRead` Pydantic schemas. Input validation and error handling help ensure that invalid requests are handled appropriately.

### 3. Additional Endpoints

The application also includes the following endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Home page |
| GET | `/health` | Health check |
| POST | `/add` | Addition |
| POST | `/subtract` | Subtraction |
| POST | `/multiply` | Multiplication |
| POST | `/divide` | Division |

## 🛠️ Getting Started

### Prerequisites

Make sure the following are installed:

- Python
- Docker Desktop
- Docker Compose
- Git

### Running the Application

1. Clone the repository:

   ```bash
   git clone <https://github.com/mab263/module12_is601>
   ```

2. Navigate to the project directory:

   ```bash
   cd module12_is601
   ```

3. Build and start the application using Docker Compose:

   ```bash
   docker compose up --build -d
   ```

4. Open the interactive API documentation in your browser:

   [http://localhost:8000/docs](http://localhost:8000/docs)

   The application can also be viewed using ReDoc:

   [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Stopping the Application

To stop the running containers, execute:

```bash
docker compose down
```

## Running Integration Tests

The project uses Pytest to run automated tests for user authentication and calculation functionality.

The integration tests use PostgreSQL through Docker Compose.

To start the application and database:

```bash
docker compose up -d
```

To run the test suite:

```bash
docker compose exec web pytest -q
```

The tests verify functionality such as:

- User registration and login
- Password hashing and verification
- Database persistence
- Creating and retrieving calculations
- Updating and deleting calculations
- Validation of invalid requests
- Appropriate HTTP status codes and error responses

To run the tests with additional output:

```bash
docker compose exec web pytest -v
```

## 📝 Manual API Testing with OpenAPI

The application can be tested manually through the FastAPI interactive documentation.

1. Start the application using Docker Compose.
2. Navigate to [http://localhost:8000/docs](http://localhost:8000/docs).
3. Expand the **users** section.
4. Test `POST /users/register` to create a new user.
5. Test `POST /users/login` to verify the user's credentials.
6. Expand the **calculations** section.
7. Test each of the five BREAD endpoints:
   - POST to create a calculation.
   - GET to retrieve calculations.
   - GET by ID to retrieve a specific calculation.
   - PUT to update an existing calculation.
   - DELETE to remove a calculation.
8. Review the responses and HTTP status codes to confirm that the endpoints work as expected.

## CI/CD Pipeline

GitHub Actions is used to automate the testing and deployment process.

The workflow:

1. Checks out the project repository.
2. Sets up the Python environment.
3. Starts a PostgreSQL service for integration testing.
4. Installs the required dependencies.
5. Runs the automated test suite.
6. Builds the Docker image.
7. Pushes the image to Docker Hub after a successful workflow.

Docker Hub credentials are stored securely as GitHub repository secrets rather than being included in the project source code.

The required secrets are:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

The GitHub Actions workflow can be viewed under the **Actions** tab of the repository.

## 🐳 Docker Hub

The Docker image for this project is published to Docker Hub.

**Docker Hub Repository:**  
[https://hub.docker.com/r/mab263/module12_is601]

To pull the image:

```bash
docker pull mab263/module12_is601:latest
```

## Project Structure

```text
module12_is601/
│
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── calculations.py
│   ├── calculation_factory.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   └── operations/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Conclusion

This project expands the original calculator API into a more complete backend application by introducing user authentication, database persistence, and full calculation management through BREAD operations. It also demonstrates automated testing, containerization, and continuous integration and deployment using GitHub Actions and Docker Hub.

This module establishes the backend functionality that will be extended with a front-end application in Module 13.