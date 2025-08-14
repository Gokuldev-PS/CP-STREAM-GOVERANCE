#!/bin/bash

# Exit on any error
set -e

# Load .env file
if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  export $(grep -v '^#' .env | xargs)
else
  echo " .env file not found. Exiting."
  exit 1
fi

# Check required variables
if [ -z "$KAFKA_REST_PROXY_URL" ]; then
  echo "❌ KAFKA_REST_PROXY_URL is not set"
  exit 1
fi

# Fetch CLUSTER_ID
CLUSTER_ID=$(curl -s "${KAFKA_REST_PROXY_URL}/v3/clusters" | jq -r '.data[0].cluster_id')

if [ -z "$CLUSTER_ID" ] || [ "$CLUSTER_ID" = "null" ]; then
  echo "❌ Could not fetch CLUSTER_ID from Kafka REST Proxy"
  exit 1
fi

echo "🧩 Kafka Cluster ID: $CLUSTER_ID"

# Create Python virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install requirements
echo "Installing dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create Kafka topic via REST Proxy

echo -e "\nCreating topic: $TOPIC_NAME with partitions_count: $PARTITIONS"

response=$(curl -s -w "\n%{http_code}" -X POST \
-H "Content-Type: application/json" \
--data "{\"topic_name\": \"${TOPIC_NAME}\", \"partitions_count\": ${PARTITIONS}}" \
"${KAFKA_REST_PROXY_URL}/v3/clusters/${CLUSTER_ID}/topics")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Response HTTP Code: $http_code"
echo "Response Body: $body"

if [[ "$http_code" =~ ^20[01]$ ]]; then
    echo "✅ Topic '$topic' created or already exists."
    echo "$body" | jq .
else
    echo "❌ Failed to create topic '$topic', HTTP $http_code"
    echo "$body" | jq .
    exit 1
fi

echo "Setup Completed! Now Run the producer.py and consumer.py applications with virtual environment venv"