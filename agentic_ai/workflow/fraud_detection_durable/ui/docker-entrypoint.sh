#!/bin/sh
# Docker entrypoint script that injects runtime configuration into the React app

set -e

# Generate runtime config script
CONFIG_SCRIPT="window.__CONFIG__ = {"

if [ -n "$API_BASE_URL" ]; then
    CONFIG_SCRIPT="${CONFIG_SCRIPT} API_BASE_URL: '${API_BASE_URL}',"
fi

if [ -n "$WS_URL" ]; then
    CONFIG_SCRIPT="${CONFIG_SCRIPT} WS_URL: '${WS_URL}',"
fi

CONFIG_SCRIPT="${CONFIG_SCRIPT} };"

echo "Injecting runtime config: $CONFIG_SCRIPT"

# Create a config.js file in the dist folder
echo "$CONFIG_SCRIPT" > /app/dist/config.js

# Inject script tag into index.html if not already present
if ! grep -q 'config.js' /app/dist/index.html; then
    sed -i 's|<head>|<head><script src="/config.js"></script>|' /app/dist/index.html
fi

# Start the server
exec serve -s dist -l 3000
