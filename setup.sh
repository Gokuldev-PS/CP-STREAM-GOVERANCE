#!/bin/bash

set -euo pipefail

echo "Starting setup..."

# Load variables
source ./variables.txt

REST_PROXY_URL="http://${REST_PROXY_HOST}:${REST_PROXY_PORT}"
SCHEMA_REGISTRY_URL="http://${SCHEMA_REGISTRY_HOST}:${SCHEMA_REGISTRY_PORT}"

echo "REST Proxy URL: $REST_PROXY_URL"
echo "Schema Registry URL: $SCHEMA_REGISTRY_URL"
echo "Cluster ID: $CLUSTER_ID"

function create_topic() {
  local topic="$1"
  local partitions="$2"
  echo -e "\nCreating topic: $topic with partitions_count: $partitions"

  response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    --data "{\"topic_name\": \"${topic}\", \"partitions_count\": ${partitions}}" \
    "${REST_PROXY_URL}/v3/clusters/${CLUSTER_ID}/topics")

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
}

function register_schema() {
  local topic="$1"
  local schema_file="$2"
  local subject="${topic}-value"

  echo -e "\nRegistering schema for subject: $subject"

  response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    --data "@${schema_file}" \
    "${SCHEMA_REGISTRY_URL}/subjects/${subject}/versions")

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  echo "Response HTTP Code: $http_code"
  echo "Response Body: $body"

  if [[ "$http_code" =~ ^20[01]$ ]]; then
    echo "✅ Schema registered for subject '$subject'."
    echo "$body" | jq .
  else
    echo "❌ Failed to register schema for subject '$subject', HTTP $http_code"
    echo "$body" | jq .
    exit 1
  fi
}

# Create topics
create_topic "$SUCCESS_TOPIC" 3
create_topic "$DLQ_TOPIC" 3

# Generate schema files
cat > success-schema.json <<EOF
{
  "schemaType": "AVRO",
  "schema": "{ \\"type\\": \\"record\\", \\"name\\": \\"t4\\", \\"fields\\": [ {\\"name\\": \\"name\\", \\"type\\": \\"string\\"}, {\\"name\\": \\"email\\", \\"type\\": \\"string\\"}, {\\"name\\": \\"ssn\\", \\"type\\": \\"string\\"} ] }",
  "ruleSet": {
    "domainRules": [
      {
        "name": "CUstomSSN",
        "kind": "CONDITION",
        "type": "CEL",
        "mode": "WRITE",
        "expr": "size(message.ssn) == 9",
        "onFailure": "DLQ",
        "params": {
          "dlq.topic": "$DLQ_TOPIC"
        }
      }
    ]
  }
}
EOF

cat > dlq-schema.json <<EOF
{
  "schemaType": "AVRO",
  "schema": "{ \\"type\\": \\"record\\", \\"name\\": \\"t4\\", \\"fields\\": [ {\\"name\\": \\"name\\", \\"type\\": \\"string\\"}, {\\"name\\": \\"email\\", \\"type\\": \\"string\\"}, {\\"name\\": \\"ssn\\", \\"type\\": \\"string\\"} ] }"
}
EOF

# Register schemas
register_schema "$SUCCESS_TOPIC" "success-schema.json"
register_schema "$DLQ_TOPIC" "dlq-schema.json"

echo -e "\n✅ Setup completed successfully!"
