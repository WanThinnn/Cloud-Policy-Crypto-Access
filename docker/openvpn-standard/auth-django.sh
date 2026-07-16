#!/bin/bash
# OpenVPN Auth-User-Pass script using Django API
# Called by OpenVPN with "auth-user-pass-verify auth-django.sh via-env"

# Ensure we have credentials
if [ -z "$username" ] || [ -z "$password" ]; then
    echo "Missing username or password"
    exit 1
fi

# Send POST request to Django web app
# We use http://web:8000 because both containers are on the same docker network
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://web:8000/api/auth/vpn_verify/ \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$username\", \"password\": \"$password\"}")

if [ "$STATUS_CODE" == "200" ]; then
    exit 0
else
    echo "VPN Authentication failed for $username. API returned $STATUS_CODE"
    exit 1
fi
