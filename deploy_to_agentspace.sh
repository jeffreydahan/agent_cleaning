#!/bin/bash

# Source environment variables from .env file
# The previous method `export $(grep -v '^#' .env | xargs)` can be fragile.
# Using `set -a` and `source` is generally more robust.
if [ -f .env ]; then
    set -a # Automatically export all variables
    source .env
    set +a # Stop automatically exporting
fi

# Get GCP Access Token
ACCESS_TOKEN=$(gcloud auth print-access-token)


# Use the following from the .env file, or a default if not set
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
COLLECTION_ID="default_collection"
ENGINE_ID="${AGENTSPACE_ENGINE_ID}"
ASSISTANT_ID="default_assistant"
REASONING_ENGINE_ID="${AGENT_ENGINE_APP_RESOURCE_ID}"
AGENT_NAME="${AGENT_NAME}"
AGENT_DESCRIPTION="${AGENT_DESCRIPTION}"



# Build API Endpoint - it must use the 'global' location hard coded
API_ENDPOINT="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/${COLLECTION_ID}/engines/${ENGINE_ID}/assistants/${ASSISTANT_ID}/agents"

# JSON Payload to create the Agent Object inside Agentspace
JSON_PAYLOAD=$(cat <<EOF
{
    "displayName": "${AGENT_NAME}",
    "description": "${AGENT_DESCRIPTION}",
    "adk_agent_definition": {
        "tool_settings": {
            "tool_description": "${TOOL_DESCRIPTION}"
        },
        "provisioned_reasoning_engine": {
            "reasoning_engine": "${REASONING_ENGINE_ID}"
        }
    }
}
EOF
)

# Execute
curl -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Goog-User-Project: ${PROJECT_ID}" \
    "${API_ENDPOINT}" \
    -d "${JSON_PAYLOAD}"

# Go to Agentspace and click Agents to view and test your agent.
# If you want to delete the Agent, just click the 3 dots on the Agent
# and select Delete.