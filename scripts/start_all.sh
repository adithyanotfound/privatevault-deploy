#!/bin/zsh

# -----------------------------------------------------------------------------
# 🚀 PrivateVault Full-Stack Startup Script (macOS/Linux)
# -----------------------------------------------------------------------------

# Colors for better output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "${BLUE}Starting all PrivateVault services...${NC}"

# Check for .venv and create if missing
if [ ! -d ".venv" ]; then
    echo "${BLUE}.venv not found. Creating virtual environment and installing dependencies...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    
    echo "${BLUE}Installing LORK...${NC}"
    pip install -e ./LORK
    
    echo "${BLUE}Installing BotBook...${NC}"
    pip install -e ./botbook.dev
    
    echo "${BLUE}Installing PrivateVault requirements...${NC}"
    pip install -r ./PrivateVault.ai/requirements.txt
    
    echo "${BLUE}Installing shared dependencies...${NC}"
    pip install pyyaml openai google-genai python-dotenv
    
    echo "${GREEN}Setup complete!${NC}"
fi

# Function to start a service in a new terminal window (macOS only)
start_service_mac() {
    local name=$1
    local dir=$2
    local command=$3
    osascript <<EOF
tell application "Terminal"
    do script "cd '$PWD/$dir' && source ../.venv/bin/activate && $command"
end tell
EOF
    echo "${GREEN}[+] Started $name${NC}"
}

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "${BLUE}macOS detected. Opening services in new terminal windows...${NC}"
    
    # 1. PrivateVault.ai (Governance) - Port 8000
    start_service_mac "PrivateVault.ai" "PrivateVault.ai" "python -m uvicorn main:app --reload --port 8000"

    # 2. BotBook.dev (Agent OS) - Port 8001
    start_service_mac "BotBook.dev" "botbook.dev" "python -m uvicorn main:app --reload --port 8001"

    # 3. LORK (Control Plane) - Port 8002
    start_service_mac "LORK" "LORK" "python -m uvicorn lork.api_server:app --reload --port 8002"

    # 4. Demo Frontend - Port 8003
    start_service_mac "Demo Frontend" "demo-frontend" "python -m http.server 8003"

else
    echo "${BLUE}Non-macOS detected. Starting services in background...${NC}"
    
    start_service_bg() {
        local name=$1
        local dir=$2
        local command=$3
        (cd "$dir" && source ../.venv/bin/activate && nohup $command > "$name.log" 2>&1 & echo $! > "../.$name.pid")
        echo "${GREEN}[+] Started $name (Background - logging to $dir/$name.log)${NC}"
    }

    start_service_bg "PrivateVault.ai" "PrivateVault.ai" "python -m uvicorn main:app --port 8000"
    start_service_bg "BotBook.dev" "botbook.dev" "python -m uvicorn main:app --port 8001"
    start_service_bg "LORK" "LORK" "python -m uvicorn lork.api_server:app --port 8002"
    start_service_bg "demo-frontend" "demo-frontend" "python -m http.server 8003"
    
    echo "\n${BLUE}All services are running in the background.${NC}"
    echo "To stop them, run: ${BLUE}pkill -f uvicorn && pkill -f 'http.server'${NC}"
fi

echo "\n${GREEN}All services requested. Waiting for initialization...${NC}"

echo "\n${GREEN}All services requested. Waiting for initialization...${NC}"
echo "--------------------------------------------------------"
echo "PrivateVault:  http://localhost:8000"
echo "BotBook:       http://localhost:8001"
echo "LORK:          http://localhost:8002"
echo "Demo Frontend: http://localhost:8003"
echo "--------------------------------------------------------"
