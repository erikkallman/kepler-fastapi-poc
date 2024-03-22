#!/bin/bash

# Set your FastAPI server address
SERVER_URL="http://localhost:8000"

# Specify the dataset ID you want to update
DATASET_ID="example_dataset_id"

# Prepare the new data as JSON
# Example new data; adjust according to your needs
NEW_DATA='{
  "points": [
    {"x": 14.540, "y": 59.320},
    {"x": 13.550, "y": 59.330}
  ]
}'

# Make a POST request to update the dataset
curl -X POST "$SERVER_URL/update_data/$DATASET_ID" \
     -H "Content-Type: application/json" \
     -d "$NEW_DATA"

echo "Dataset update request sent."
