#!/bin/bash

# Check if OPENAI_API_TYPE is "custom"
if [[ "$OPENAI_API_TYPE" == "custom" ]]; then
    # Check if OPENAI_API_KEY is unset or empty
    if [[ -z "$OPENAI_API_KEY" ]]; then
        echo "OPENAI_API_KEY is not set. Logging in using Azure CLI..."
        az login -o none
    else
        echo "Using provided api key for OpenAI client. Skipping az login."
    fi
else
    echo "Using default OpenAI client."
fi

python -u -m main