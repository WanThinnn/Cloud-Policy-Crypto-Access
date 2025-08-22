#!/bin/bash

# generate_secrets.sh - Generate random secrets for .env file

echo "Generating secrets for Cloud Firestore Crypto Access Backend..."
echo ""

# Generate JWT Secret Key
JWT_SECRET=$(openssl rand -hex 32)
echo "JWT_SECRET_KEY=$JWT_SECRET"

# Generate System Service Token  
SYSTEM_TOKEN=$(openssl rand -hex 32)
echo "SYSTEM_SERVICE_TOKEN=$SYSTEM_TOKEN"

echo ""
echo "Copy these values to your env/.env file:"
echo "----------------------------------------"
echo "JWT_SECRET_KEY=$JWT_SECRET"
echo "SYSTEM_SERVICE_TOKEN=$SYSTEM_TOKEN"
echo ""
echo "Or run this command to update .env automatically:"
echo "sed -i 's/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/' env/.env"
echo "sed -i 's/SYSTEM_SERVICE_TOKEN=.*/SYSTEM_SERVICE_TOKEN=$SYSTEM_TOKEN/' env/.env"
