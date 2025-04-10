#!/bin/bash

# SetlistGenie Deployment Script
# This script automates the process of deploying the SetlistGenie app to Cloud Run
# with cost-optimized settings

echo "==== SetlistGenie Deployment Script ===="
echo "This will deploy the application to Cloud Run in pauliecee-ba4e0 project"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Verify we're in the right project
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "pauliecee-ba4e0" ]; then
    echo "Switching to pauliecee-ba4e0 project..."
    gcloud config set project pauliecee-ba4e0
fi

# Check if service account file exists
if [ ! -f "./firebase-service-account.json" ]; then
    echo "Warning: firebase-service-account.json not found."
    echo "You'll need to set FIREBASE_ADMIN_CREDENTIALS manually after deployment."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if .env file exists for local vars
if [ -f "./.env" ]; then
    source ./.env
    echo "Loaded environment variables from .env file"
else
    echo "Warning: No .env file found. Using default or empty values."
fi

# Build the container
echo "Building container image..."
gcloud builds submit --tag gcr.io/pauliecee-ba4e0/setlistgenie

# Deploy to Cloud Run with cost-optimized settings
echo "Deploying to Cloud Run..."
gcloud run deploy setlistgenie \
  --image gcr.io/pauliecee-ba4e0/setlistgenie \
  --platform managed \
  --region us-east1 \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars "FLASK_SECRET_KEY=${FLASK_SECRET_KEY:-$(openssl rand -base64 32)}" \
  --set-env-vars "SUPABASE_URL=${SUPABASE_URL:-https://cqlldqgxghuvbtmlaiec.supabase.co}" \
  --set-env-vars "SUPABASE_KEY=${SUPABASE_KEY:-your_supabase_key_here}"

# Set Firebase Admin credentials if available
if [ -f "./firebase-service-account.json" ]; then
    echo "Setting Firebase Admin credentials..."
    FIREBASE_CREDENTIALS=$(cat ./firebase-service-account.json | base64 -w 0)
    gcloud run services update setlistgenie \
      --update-env-vars "FIREBASE_ADMIN_CREDENTIALS=${FIREBASE_CREDENTIALS}"
    echo "Firebase credentials set successfully"
else
    echo "Skipping Firebase credentials setup"
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe setlistgenie --platform managed --region us-east1 --format 'value(status.url)')

echo "==== Deployment Complete ===="
echo "SetlistGenie is now available at: $SERVICE_URL"
echo "To map your custom domain (setlist.pauliecee.com), run:"
echo "gcloud beta run domain-mappings create --service setlistgenie --domain setlist.pauliecee.com --region us-east1"
