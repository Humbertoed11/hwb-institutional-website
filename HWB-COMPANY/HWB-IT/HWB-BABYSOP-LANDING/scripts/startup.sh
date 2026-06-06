#!/bin/bash
echo "--- HEXGROWTH: Initiating hex.dev Startup Sequence ---"
# Check if container is running
docker ps | grep hex_web_app > /dev/null
if [ $? -eq 0 ]; then
    echo "SUCCESS: hex_web_app container is active."
else
    echo "FAILURE: hex_web_app is down. Attempting restart..."
    cd /home/humbertoed/hexgrowth && docker-compose up -d
fi
echo "--- hex.dev Systems Operational ---"
