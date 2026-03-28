#!/bin/zsh

# -----------------------------------------------------------------------------
# 🛑 PrivateVault Stop Services Script (macOS/Linux)
# -----------------------------------------------------------------------------

# Colors for better output
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "${RED}Stopping all PrivateVault services...${NC}"

# Find and kill uvicorn processes (Ports 8000, 8001, 8002)
echo "Killing uvicorn servers..."
pkill -f "uvicorn.*main:app.*800"
pkill -f "uvicorn.*lork.api_server:app.*800"

# Find and kill http.server (Port 8003)
echo "Killing demo frontend server..."
pkill -f "python.*http.server.*8003"

echo "${RED}All services stopped.${NC}"
