import logging
import os
import sys

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions
from google.cloud import storage
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp


from analytics_agent.agent import root_agent 

# --- Flags for Command Line Arguments ---
FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket name for staging.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID (for delete).")

flags.DEFINE_bool("create", False, "Create a new agent.")
flags.DEFINE_bool("delete", False, "Delete an existing agent.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete"])


AGENT_WHL_FILE = "analytics_agent-0.1-py3-none-any.whl" 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def setup_staging_bucket(project_id: str, location: str, bucket_name: str) -> str:
    """
    Checks if the staging bucket exists, creates it if not, and ensures uniform access.
    """
    storage_client = storage.Client(project=project_id)
    try:
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket:
            logger.info("Staging bucket gs://%s already exists.", bucket_name)
        else:
            logger.info("Creating staging bucket gs://%s...", bucket_name)
            new_bucket = storage_client.create_bucket(
                bucket_name, project=project_id, location=location
            )
            logger.info("Successfully created staging bucket gs://%s.", new_bucket.name)
            # Enable uniform bucket-level access for consistency
            new_bucket.iam_configuration.uniform_bucket_level_access_enabled = True
            new_bucket.patch()
            logger.info("Enabled uniform bucket-level access for gs://%s.", new_bucket.name)
    except google_exceptions.Forbidden as e:
        logger.error(
            "Permission denied for bucket gs://%s. Ensure 'Storage Admin' role. Error: %s",
            bucket_name, e
        )
        raise
    except google_exceptions.Conflict:
        logger.warning("Bucket gs://%s likely exists but owned by another project or recently deleted. Proceeding assuming access.", bucket_name)
    except google_exceptions.ClientError as e:
        logger.error("Failed to create or access bucket gs://%s. Error: %s", bucket_name, e)
        raise
    return f"gs://{bucket_name}"


def create_agent(env_vars: dict[str, str], project_id: str, location: str, staging_bucket_uri: str) -> None:
    """Creates and deploys the agent."""
    logger.info("Initializing Vertex AI for project %s in %s with staging bucket %s", project_id, location, staging_bucket_uri)
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=staging_bucket_uri,
    )

    adk_app = AdkApp(
        agent=root_agent, # This is your primary agent instance
        enable_tracing=False, # Set to True for debugging/monitoring
    )

    if not os.path.exists(AGENT_WHL_FILE):
        logger.error("Agent wheel file not found at: %s", AGENT_WHL_FILE)
        logger.error("Please build the wheel file first. Refer to the instructions below.")
        sys.exit(1) # Exit if the wheel file is not found

    logger.info("Deploying agent using wheel file: %s", AGENT_WHL_FILE)

    remote_agent = agent_engines.create(
        adk_app,
        display_name="analytics Agent System", # Give your agent a meaningful display name
        requirements=[AGENT_WHL_FILE], # Your custom agent code package
        # extra_packages is typically used for additional non-PyPI dependencies,
        # but can also be used if your wheel is not specified in requirements
        # For simplicity, if your wheel is in requirements, this might be redundant or could be simplified.
        # However, it doesn't hurt to keep it for local wheel files.
        extra_packages=[AGENT_WHL_FILE],
        env_vars=env_vars,
        # You might also specify service_account if you need a specific one
        # service_account="your-service-account@your-project.iam.gserviceaccount.com"
    )
    logger.info("Successfully created remote agent: %s", remote_agent.resource_name)
    print(f"\nSuccessfully created agent: {remote_agent.resource_name}")


def delete_agent(resource_id: str, project_id: str, location: str) -> None:
    """Deletes the specified agent."""
    logger.info("Initializing Vertex AI for project %s in %s to delete agent %s", project_id, location, resource_id)
    vertexai.init(
        project=project_id,
        location=location,
    )
    logger.info("Attempting to delete agent: %s", resource_id)
    try:
        remote_agent = agent_engines.get(resource_id)
        remote_agent.delete(force=True) # force=True will delete even if there are active deployments
        logger.info("Successfully deleted remote agent: %s", resource_id)
        print(f"\nSuccessfully deleted agent: {resource_id}")
    except google_exceptions.NotFound:
        logger.error("Agent with resource ID %s not found.", resource_id)
        print(f"\nAgent not found: {resource_id}")
    except Exception as e:
        logger.error("An error occurred while deleting agent %s: %s", resource_id, e)
        print(f"\nError deleting agent {resource_id}: {e}")


def main(argv: list[str]) -> None:
    """Main execution function."""
    load_dotenv() # Load environment variables from .env file

    project_id = FLAGS.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = FLAGS.location or os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket_name = FLAGS.bucket or os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    # If bucket_name is still not set, default to a project-specific name
    if not bucket_name and project_id:
        bucket_name = f"{project_id}-analytics-agent-staging"
        logger.info("Defaulting GCS bucket name to: %s", bucket_name)
    elif not bucket_name:
         print("\nError: GCS Bucket Name is required. Set GOOGLE_CLOUD_STORAGE_BUCKET env var or use --bucket flag.")
         sys.exit(1)


    # Environment variables to pass to the deployed agent runtime
    # These typically store model names, dataset IDs, etc.
    env_vars = {
        "ROOT_AGENT_MODEL": os.getenv("ROOT_AGENT_MODEL"),
        "analytics_AGENT_MODEL": os.getenv("analytics_AGENT_MODEL"),
    
        # Add any other specific environment variables your agents need
        # e.g., "BQ_DATASET_ID": os.getenv("BQ_DATASET_ID"),
        # IMPORTANT: Do NOT include GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION here,
        # as they are automatically set by the Agent Engine backend.
    }
    # Filter out None values from env_vars to avoid passing empty strings
    env_vars = {k: v for k, v in env_vars.items() if v is not None}


    logger.info("Using PROJECT: %s", project_id)
    logger.info("Using LOCATION: %s", location)
    logger.info("Using BUCKET NAME: %s", bucket_name)

    # --- Input Validation ---
    if not project_id:
        print("\nError: Missing required GCP Project ID. Set GOOGLE_CLOUD_PROJECT env var or use --project_id flag.")
        sys.exit(1)
    if not location:
        print("\nError: Missing required GCP Location. Set GOOGLE_CLOUD_LOCATION env var or use --location flag.")
        sys.exit(1)
    if not (FLAGS.create or FLAGS.delete):
        print("\nError: You must specify either --create or --delete flag.")
        sys.exit(1)
    if FLAGS.delete and not FLAGS.resource_id:
        print("\nError: --resource_id is required when using the --delete flag.")
        sys.exit(1)
    # --- End Input Validation ---

    try:
        staging_bucket_uri = None
        if FLAGS.create:
            staging_bucket_uri = setup_staging_bucket(project_id, location, bucket_name)
            create_agent(env_vars, project_id, location, staging_bucket_uri)
        elif FLAGS.delete:
            delete_agent(FLAGS.resource_id, project_id, location)

    except google_exceptions.Forbidden as e:
        print(
            "Permission Error: Ensure the service account/user has necessary "
            "permissions (e.g., Storage Admin, Vertex AI User, Vertex AI Agent Engine Developer)."
            f"\nDetails: {e}"
        )
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\nFile Error: {e}")
        print(
            "Please ensure the agent wheel file exists in the directory where this script is run."
        )
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        logger.exception("Unhandled exception in main:") # Log the full traceback
        sys.exit(1)


if __name__ == "__main__":
    app.run(main)