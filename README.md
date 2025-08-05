# analytics Agent

This repository hosts a multi-agent system designed to assist users with data analysis and visualization tasks using Google's Agent Development Kit (ADK).

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Overview

The system consists of a `Root Agent` that acts as a central dispatcher, understanding user intent and delegating complex data analysis and plotting requests to a specialized `analytics Agent`.

## Architecture

- **Root Agent (`DA_Agent`):**
    - Built with `gemini-2.5-flash`.
    - Responsible for interpreting user queries.
    - Delegates plotting and complex analysis tasks to the `analytics_agent` via the `call_analytics_agent` tool.
    - Provides confirmation messages to the user upon successful task completion.

- **analytics Agent (`analytics_agent`):**
    - Specialized in data manipulation and visualization.
    - Utilizes the `vertexaicodeexecutor` to run Python code (e.g., using `pandas` and `matplotlib`) in a secure sandbox environment to generate plots.
    - Designed to return specific data insights or confirmation of plot generation.

## Features

- **Intelligent Delegation:** Automatically routes data visualization requests to the appropriate sub-agent.
- **Data Plotting:** Generates various types of charts (e.g., bar charts, line graphs) based on user-provided data.
- **Interactive Environment:** (Potentially, if running in a Colab-like environment) Visualizes plots directly in the output.

## Setup and Installation

To get this agent system running locally:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Prudhvi-58/analytics-Agent.git](https://github.com/Prudhvi-58/analytics-Agent.git)
    cd analytics-Agent
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    (Make sure you have a `requirements.txt` file listing all your Python dependencies, e.g., `google-generativeai`, `google-cloud-aiplatform`, `pandas`, `matplotlib`, `google-adk`).

4.  **Google Cloud Project Setup:**
    - Ensure you have a Google Cloud Project with Vertex AI API enabled.
    - Set up Application Default Credentials (ADC) for authentication. You can do this by running `gcloud auth application-default login` in your terminal.
    - Ensure your project has the necessary permissions (e.g., Vertex AI User, Service Usage Consumer).

5.  **Environment Variables:**
    - Create a `.env` file in the root of your project.
    - Add your Google Cloud Project ID and potentially other API keys:
      ```
      GOOGLE_CLOUD_PROJECT_ID=your-project-id
      GOOGLE_GENAI_USE_VERTEXAI=TRUE
      GOOGLE_CLOUD_LOCATION=us-central1
      # Add other environment variables as needed, e.g., model names if not hardcoded
      ```
      **NOTE:** The `.env` file is in `.gitignore` and should **not** be committed to your repository.

## Usage

To run the agents:

1.  **Start the agent application:**
    ```bash
    adk web 
    ```

2.  **Interact with the agent:**
    Once the agent is running, you can typically interact with it via a local web interface (e.g., `http://localhost:8080`) or through a CLI, depending on your ADK setup.

    **Example Query:**
    "Can you plot the website visits by month from this data?
    `{ \"month\": [\"Jan\", \"Feb\", \"Mar\", \"Apr\"], \"website_visits\": [12000, 13500, 15000, 14800] }`"

    The agent should respond with a confirmation that the plot has been generated, which you can then view in your local.

## Deployment to Agent Engine

    After you have developed and tested your agent locally, you can deploy it to the Agent Engine for production use.

1.  **Package your agent:**
    First, you need to create a .whl file for your agent. From the deployment directory, run this command:
    ```bash
    poetry build --format=wheel --output=deployment
    ```
    This will create a file named analytics_agent-0.1-py3-none-any.whl in the deployment directory.

2.  **Deploy using the provided script:**
    Then run the below command to create a staging bucket in your GCP project and deploy the agent to Vertex AI Agent Engine:

    ```bash
    cd deployment/
    python3 deploy.py --create
    ```
When this command returns, if it succeeds it will print an AgentEngine resource name that looks something like this:
`projects/************/locations/us-central1/reasoningEngines/******`