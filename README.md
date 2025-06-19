# Dockerized FastAPI Task Tracker: A Hexagonal Architecture-Powered Task & Goal Management System

This project presents a task and goal tracking system that is extremely flexible. Start scheduling recurring tasks or goals with adaptive deadline distributions, and replace manual tasks with automated scripts only when you have the time.

It uses **FastAPI** and the principles of **Hexagonal Architecture (Ports and Adapters)** and **Domain-Driven Design (DDD)** to stay extremely adaptable when used with external dependencies.

You can write a simple adapter for **Model Context Protocol** and let LLMs perform tasks. Or implement browser automation with Selenium by writing a new strategy adapter. Its core purpose is to serve as a highly maintainable and extensible backend service for task and goal management.

By using a **State pattern** for task status transitions and flexible **SchedulingPolicy**, the system is designed for adaptability and future enhancements.

## Table of Contents

1.  [Features](#features)
2.  [Architectural Highlights](#architectural-highlights)
    * [Hexagonal Architecture (Ports & Adapters)](#hexagonal-architecture-ports--adapters)
    * Domain-Driven Design (DDD)
    * State Pattern for Task Status
3.  [Technology Stack](#technology-stack)
4.  [Local Development (Dockerized / Uvicorn)](#local-development-dockerized--uvicorn)
5.  [Deploying to Cloud (Amazon Web Services)](#deploying-to-cloud-amazon-web-services)
6.  [Endpoints](#endpoints)
7.  [Testing](#testing)

## 1. Features

* **Goal Management:** Define and track recurring goals with flexible scheduling policies (e.g., fixed intervals, deadline-driven distributions).
* **Automated Task Generation:** Automatically generates concrete tasks based on defined goals and their scheduling policies.
* **Task Lifecycle Management:** Comprehensive status tracking for tasks (Waiting, InProgress, Completed, Failed, Skipped) with controlled transitions.
* **Audit Logging:** Detailed logs for all task status changes, ensuring traceability and accountability.
* **Pluggable Strategies:** Supports various strategies for performing and checking tasks (e.g., browser automation(planned), custom scripts, manual prompts).
* **Platform & Account Abstraction:** Manages tasks across different external platforms and associated user accounts.

## 2. Architectural Highlights

### Hexagonal Architecture (Ports & Adapters)

Project applies the Hexagonal Architecture, making sure the core domain remains independent of external concerns.

* **Domain Core:** python models `Platform`, `Account`, `Goal`, `Task`, `TaskLog`, value objects (e.g., `SchedulingPolicy`), and `Domain Services`. defines the business rules and logic.
* **Ports (Interfaces):** Defined as `Protocol`s in Python. Examples: `ITaskRepository`, `IGoalRepository`, `IScheduler`, `IStrategyFactory`, `ILogger`.
* **Adapters:** Concrete implementations of the ports, including:
    * **Persistence Adapters:** SQLAlchemy for data storage.
    * **Scheduler Adapters:** APScheduler for task scheduling (for now).
    * **Perform/Check Strategy Adapters:** `ScriptRunner` for executing scripts, and manual prompt for user interaction.
    * **UI Adapters:** FastAPI serves as the primary web interface, exposing the application's use cases.

## 3. Technology Stack

* **Backend Framework:** FastAPI
* **Asynchronous Web Server:** Uvicorn
* **Database:** Sqlite (Planned: PostgreSQL) (via SQLAlchemy ORM and alembic for migrations)
* **Dependency Management:** `pip` / `requirements.txt`
* **Containerization:** Docker
* **Cloud Deployment:** Amazon Web Services (AWS)

## 4. Local Development (Dockerized / Uvicorn)
For uvicorn, running the application is as simple as using `python main.py`. But you need to first create a virtual environment, install the dependencies, and run the migrations with alembic.

For docker, run the following command:
```bash
docker-compose build
docker-compose up
```
Your database will persist in the db folder on your host.

For all future changes to the models use below commands (for docker enter container's bash and run the command there):

```
alembic revision --autogenerate -m "new message"
alembic upgrade head
```

## 5. Deploying to Cloud (Amazon Web Services)

### 1.**Build and Push Your Docker Image to Amazon Web Services ECR**

1.  **Create an ECR Repository**
    In AWS Console, go to ECR (Elastic Container Registry) and create a new repository (e.g. `task-tracker` ).

2.  **Authenticate Docker to ECR**
```bash
aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.<your-region>.amazonaws.com
```

3.  **Build and Push Docker Image**
```bash
docker build -t task-tracker .
docker tag task-tracker:latest <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/task-tracker:latest
docker push <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/task-tracker:latest
```

### 2.**Deploy to AWS**

#### Option 1: ECS
Create a new ECS cluster, create task definition using the ECR image, set up a service to run the container. Create an EFS volume and mount to /app/db

#### Option 2: EC2
Launch an EC2 instance. Pull your image if you created it, or just pull your repo and build&run a container:
```bash
aws ecr get-login-password --region YOUR_REGION | \
docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com
docker pull YOUR_AWS_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/YOUR_IMAGE_NAME:tag
docker run -d -p 8000:8000 YOUR_IMAGE_NAME
```

And use nginx for reverse proxy. Conf example:
```nginx
server {
    listen 80; # or use 443 after ssl setup
    server_name mywebsite.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Endpoints

### **Dashboard**

| Method                     | Path                            | Description                                                | Parameters (Path/Form)                                       |
| :------------------------- | :------------------------------ | :--------------------------------------------------------- | :----------------------------------------------------------- |
| GET (Returns HTMLResponse)  | /                               | Displays the main dashboard with an overview of platforms. | None                                                         |
| POST (Returns JSONResponse) | /services/{service\_name}/start | Starts a specified service.                                | service\_name: string (path)Returns: {"status": "started"} or {"error": "Service not found"} |
| GET (Returns HTMLResponse)  | /all-tasks                      | Displays a list of all tasks.                              | None                                                         |


### **Goals**

| Method                         | Path                     | Description                                                  | Parameters (Path/Form)                                       |
| :----------------------------- | :----------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| GET (Returns HTMLResponse)      | /goals                   | Displays a list of all created goals.                        | None                                                         |
| GET (Returns HTMLResponse)      | /goals/add               | Displays the form for adding a new goal.                     | None                                                         |
| POST (Returns RedirectResponse) | /goals/add               | Handles the submission of the "add goal" form, creating a new goal. | Form data: platform\_id (integer), description (string), start\_date (date), policy\_type (string), interval\_days (integer, optional), deadline\_date (date, optional), total\_occurrences (integer, optional), freeze\_on\_miss (boolean), account\_ids (list of integers, optional), task\_distribution\_strategy (string), catchup\_strategy (string), execution\_strategy (string), execution\_script\_content (string), execution\_script\_env\_vars (string, KEY=VALUE\\nKEY2=VALUE2 format to be parsed into dict) |
| GET (Returns HTMLResponse)      | /goals/{goal\_id}/edit   | Displays the form to edit an existing goal, pre-filled with its data. | goal\_id: integer (path)                                     |
| POST (Returns RedirectResponse) | /goals/{goal\_id}/edit   | Handles the submission of the "edit goal" form, updating an existing goal. | goal\_id: integer (path)Form data: same as /goals/add plus check\_strategy (string), check\_script\_content (string), check\_script\_env\_vars (string, KEY=VALUE\\nKEY2=VALUE2 format to be parsed into dict) |
| POST (Returns RedirectResponse) | /goals/{goal\_id}/delete | Handles the deletion of a goal.                              | goal\_id: integer (path)                                     |


### **Platforms & Accounts**

| Method                         | Path                                   | Description                                                  | Parameters (Path/Form)                                       |
| :----------------------------- | :------------------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| GET (Returns HTMLResponse)      | /platforms                             | Displays a list of all managed platforms.                    | None                                                         |
| POST (Returns RedirectResponse) | /platforms/add                         | Adds a new platform.                                         | Form data: name: string (required), config: string (optional, default "{}") |
| GET (Returns HTMLResponse)      | /platforms/{platform\_id}/accounts     | Displays a list of accounts associated with a specific platform. | platform\_id: integer (path)                                 |
| POST (Returns RedirectResponse) | /platforms/{platform\_id}/accounts/add | Adds a new account to a specified platform.                  | platform\_id: integer (path)Form data: username: string (required), notes: string (optional) |
| POST (Returns RedirectResponse) | /accounts/{account\_id}/delete         | Deletes an account.                                          | account\_id: integer (path)Form data: platform\_id: integer (required) |
| GET (Returns HTMLResponse)      | /platforms/{platform\_id}/edit         | Displays the form to edit an existing platform.              | platform\_id: integer (path)                                 |
| POST (Returns RedirectResponse) | /platforms/{platform\_id}/edit         | Handles the submission of the "edit platform" form, updating an existing platform. | platform\_id: integer (path)Form data: name: string (required), config: string (optional, default "{}") |


### **Tasks**

| Method                         | Path                            | Description                                                  | Parameters (Path/Form)                                       |
| :----------------------------- | :------------------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| POST (Returns RedirectResponse) | /tasks/{task\_id}/run-execution | Schedules the execution script for a task to run in the background. | task\_id: integer (path)Form data: redirect\_url: string (optional, default "/all-tasks") |
| POST (Returns RedirectResponse) | /tasks/generate-due             | Triggers the generation of new tasks based on due goals in the background. | Form data: redirect\_url: string (optional, default "/all-tasks") |
| POST (Returns RedirectResponse) | /tasks/{task\_id}/run-check     | Schedules the check script for a task to run in the background. | task\_id: integer (path)Form data: redirect\_url: string (optional, default "/all-tasks") |
| POST (Returns RedirectResponse) | /tasks/{task\_id}/skip          | Marks a task as skipped.                                     | task\_id: integer (path)Form data: redirect\_url: string (optional, default "/all-tasks"), notes: string (optional) |
| POST (Returns RedirectResponse) | /tasks/{task\_id}/complete      | Marks a task as complete.                                    | task\_id: integer (path)Form data: redirect\_url: string (optional, default "/all-tasks"), notes: string (optional) |
| POST (Returns RedirectResponse) | /tasks/{task\_id}/start         | Marks a task as in progress.                                 | task\_id: integer (path)Form data: redirect\_url: string (optional, default "/all-tasks") |
| POST (Returns RedirectResponse) | /tasks/{task\_id}/fail          | Marks a task as failed.                                      | task\_id: integer (path)Form data: redirect\_url: string (optional, default "/all-tasks"), notes: string (optional) |
| GET (Returns HTMLResponse)      | /tasks/{task\_id}/logs          | Displays the logs for a specific task.                       | task\_id: integer (path)                                     |


*Content to be filled with API endpoint documentation (e.g., `/goals/`, `/tasks/`, `/tasks/{task_id}/complete`, etc.).*

## 7. Testing

*Work in progress.*
