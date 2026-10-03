#!/bin/bash
# Double-click to start the Video Factory: launches the runner + opens the dashboard.
# Close this Terminal window to stop.
cd "$(dirname "$0")"
echo "Starting Video Factory…"
( sleep 1; open "http://localhost:4300/dashboard.html" ) &
exec node runner.mjs
