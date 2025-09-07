gcloud auth login
gcloud auth application-default login

# This script deploys the camera tool to Cloud Run using Secret Manager
# and then deploys the main agent to Agent Engine.

# --- Preamble: Enable APIs and Load Environment ---
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Load environment variables from .env file in the project root
cd ~/code/agent_cleaning
source .env

# --- Secret Manager Setup ---
# This section creates secrets in Google Secret Manager and grants the
# Cloud Run service account access. It's safe to re-run this script.
PROJECT_NUMBER=$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Helper function to create/update secrets and grant permissions
create_or_update_secret() {
  local secret_name=$1
  local secret_value=$2
  echo "--- Setting up secret: $secret_name ---"
  gcloud secrets create "$secret_name" --replication-policy="automatic" --project="$GOOGLE_CLOUD_PROJECT" &>/dev/null || echo "Secret '$secret_name' already exists. Updating version."
  echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=- --project="$GOOGLE_CLOUD_PROJECT"
  gcloud secrets add-iam-policy-binding "$secret_name" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$GOOGLE_CLOUD_PROJECT" --condition=None &>/dev/null || echo "IAM binding for '$secret_name' already exists."
}

# Create/update all necessary secrets
create_or_update_secret "rtsp-username" "$RTSP_USERNAME"
create_or_update_secret "rtsp-password" "$RTSP_PASSWORD"
create_or_update_secret "rtsp-ip-address" "$RTSP_IP_ADDRESS"
create_or_update_secret "rtsp-stream-path" "$RTSP_STREAM_PATH"
create_or_update_secret "record-duration-seconds" "$RECORD_DURATION_SECONDS"
create_or_update_secret "gcs-cleaning-bucket" "$GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET"
echo "--- Secret setup complete ---"

# --- Build and Deploy Camera Tool Container ---
gcloud artifacts repositories create "$GOOGLE_CLOUD_ARTIFACT_REPO" --repository-format=docker --location="$GOOGLE_CLOUD_LOCATION" --description="Docker repository" &>/dev/null || echo "Artifact Registry repo '$GOOGLE_CLOUD_ARTIFACT_REPO' already exists."

cd ~/code/agent_cleaning/camera_tool_container
gcloud builds submit --tag "$GOOGLE_CLOUD_LOCATION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$GOOGLE_CLOUD_ARTIFACT_REPO/camera-tool-image:latest" .

echo "--- Deploying to Cloud Run with secrets ---"
gcloud run deploy camera-tool-svc \
  --image "$GOOGLE_CLOUD_LOCATION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$GOOGLE_CLOUD_ARTIFACT_REPO/camera-tool-image:latest" \
  --platform managed \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" \
  
  
# Get the URL of the deployed service and export it for the next step
cd ~/code
export CAMERA_TOOL_SERVICE_URL=$(gcloud run services describe camera-tool-svc --platform managed --region "$GOOGLE_CLOUD_LOCATION" --format 'value(status.url)')
echo "Camera Tool Service URL: $CAMERA_TOOL_SERVICE_URL"
create_or_update_secret "camera-tool-service-url" "$CAMERA_TOOL_SERVICE_URL"

# update the agent_cleaning/.env file with this value.  If the value is already present in the file, update it.
if grep -q "^CAMERA_TOOL_SERVICE_URL=" agent_cleaning/.env; then
  sed -i "s|^CAMERA_TOOL_SERVICE_URL=.*|CAMERA_TOOL_SERVICE_URL=\"$CAMERA_TOOL_SERVICE_URL\"|" agent_cleaning/.env
else
  echo "CAMERA_TOOL_SERVICE_URL=\"$CAMERA_TOOL_SERVICE_URL\"" >> agent_cleaning/.env
fi

# --- Test the Deployed Cloud Run Service ---
echo "--- Testing camera-tool-svc with room=demobooth ---"
curl -m 70 -X POST "$CAMERA_TOOL_SERVICE_URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"room": "demobooth"}'
echo "\n--- Test complete ---"

# Deploy to Agent Engine
cd ~/code
python3 -m agent_cleaning.deploy_to_agent_engine
source agent_cleaning/.env
echo $AGENT_ENGINE_APP_RESOURCE_ID

# Query from Agent Engine
python3 agent_cleaning/query_agent_engine.py 

# Deploy to Agentspace
cd ~/code/agent_cleaning
bash deploy_to_agentspace.sh

# Remove from Agentspace (based on Agent Name in env file; if updated, run the
# source command)
cd ~/code/agent_cleaning
bash remove_from_agentspace.sh


# if session restarts:
source ~/code/agent_cleaning/.venv/bin/activate
source ~/code/agent_cleaning/.env

# redeploy cloud run with new IP:
RTSP_IP_ADDRESS="$(curl -s icanhazip.com)" #set the new IP address
echo $RTSP_IP_ADDRESS
sed -i.bak "s/^RTSP_IP_ADDRESS=.*/RTSP_IP_ADDRESS=\"${RTSP_IP_ADDRESS}\"/" .env # update env file
create_or_update_secret "rtsp-ip-address" "$RTSP_IP_ADDRESS" # update the secret
gcloud run deploy camera-tool-svc \
  --image "$GOOGLE_CLOUD_LOCATION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$GOOGLE_CLOUD_ARTIFACT_REPO/camera-tool-image:latest" \
  --platform managed \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
