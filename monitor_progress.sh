#!/bin/bash
# Live progress monitor for ingestion pipeline

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to get progress
get_progress() {
    local total=$(find "10K2K v2" -name "*.txt" -type f 2>/dev/null | wc -l | tr -d ' ')
    
    if [ -f "checkpoints/ingest_transcripts.json" ]; then
        local processed=$(python3 -c "
import json
try:
    with open('checkpoints/ingest_transcripts.json') as f:
        data = json.load(f)
    print(len(data.get('processed', [])))
except:
    print(0)
" 2>/dev/null)
    else
        local processed=0
    fi
    
    echo "$processed $total"
}

# Function to get current file being processed
get_current_file() {
    tail -1 logs/ingest_all.log 2>/dev/null | grep -o "Processing: [^ ]*" | cut -d' ' -f2 || echo "Starting..."
}

# Function to get recent status
get_recent_status() {
    tail -3 logs/ingest_all.log 2>/dev/null | grep -E "✓|✗|Processing|Progress" | tail -1 || echo "Initializing..."
}

# Function to check if ingestion is running
is_running() {
    docker ps --format "{{.Names}}" | grep -q "ingest" && echo "yes" || echo "no"
}

# Clear screen and show header
clear
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}          📊 LIVE INGESTION PROGRESS MONITOR              ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Main loop
while true; do
    # Move cursor to top of display area
    tput cup 3 0
    
    # Get progress
    read processed total <<< $(get_progress)
    
    if [ "$total" -eq 0 ]; then
        echo -e "${RED}Error: No transcript files found!${NC}"
        sleep 2
        continue
    fi
    
    # Calculate percentage
    if [ "$total" -gt 0 ]; then
        percentage=$(awk "BEGIN {printf \"%.1f\", ($processed/$total)*100}")
        remaining=$((total - processed))
    else
        percentage=0
        remaining=$total
    fi
    
    # Check if running
    running=$(is_running)
    
    # Status indicator
    if [ "$running" = "yes" ]; then
        status_indicator="${GREEN}●${NC} RUNNING"
    else
        status_indicator="${RED}○${NC} STOPPED"
    fi
    
    # Display status
    echo -e "Status: $status_indicator"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Progress info
    printf "%-25s %s\n" "Total files:" "$total"
    printf "%-25s ${GREEN}%s${NC}\n" "✅ Processed:" "$processed"
    printf "%-25s ${YELLOW}%s${NC}\n" "⏳ Remaining:" "$remaining"
    echo ""
    
    # Progress bar (50 chars wide)
    bar_length=50
    filled=$(awk "BEGIN {printf \"%.0f\", ($percentage/100)*$bar_length}")
    empty=$((bar_length - filled))
    
    bar="${GREEN}"
    for ((i=0; i<filled; i++)); do bar+="█"; done
    bar+="${NC}${YELLOW}"
    for ((i=0; i<empty; i++)); do bar+="░"; done
    bar+="${NC}"
    
    echo -e "Progress: [$bar] ${percentage}%"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Current activity
    current_file=$(get_current_file)
    recent_status=$(get_recent_status)
    
    echo -e "Current file: ${BLUE}$current_file${NC}"
    echo -e "Status:        $recent_status"
    echo ""
    
    # Time estimate
    if [ "$processed" -gt 0 ] && [ "$running" = "yes" ]; then
        # Rough estimate: 30 seconds per file average
        avg_time=30
        estimated_seconds=$((remaining * avg_time))
        estimated_minutes=$((estimated_seconds / 60))
        
        if [ $estimated_minutes -lt 60 ]; then
            echo -e "⏱️  Estimated time remaining: ~${estimated_minutes} minutes"
        else
            hours=$((estimated_minutes / 60))
            mins=$((estimated_minutes % 60))
            echo -e "⏱️  Estimated time remaining: ~${hours}h ${mins}m"
        fi
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "Press ${YELLOW}Ctrl+C${NC} to exit monitor"
    echo ""
    
    # Wait before next update
    sleep 2
done

