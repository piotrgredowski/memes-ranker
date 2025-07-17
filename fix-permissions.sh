#!/bin/bash

# Fix permissions for Docker volume mounts
# This script should be run on the host system

echo "Fixing permissions for Docker volume mounts..."

# Create directories if they don't exist
mkdir -p data logs

# Set ownership to match the container user (uid 999, gid 999)
# This corresponds to the 'appuser' in the container
sudo chown -R 999:999 data logs

# Set appropriate permissions
sudo chmod -R 755 data logs

echo "Permissions fixed!"
echo "You can now run: docker-compose up -d"
