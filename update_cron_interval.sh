#!/bin/bash
# Script untuk update interval cron setelah mengubah .env

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Updating Cron Interval...${NC}"

# Get current interval from .env
CRON_INTERVAL=15
if [[ -f ".env" ]]; then
    ENV_INTERVAL=$(grep "^CRON_INTERVAL_MINUTES=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
    if [[ -n "$ENV_INTERVAL" && "$ENV_INTERVAL" =~ ^[0-9]+$ ]]; then
        CRON_INTERVAL=$ENV_INTERVAL
        echo -e "${GREEN}✅ Found CRON_INTERVAL_MINUTES=$CRON_INTERVAL in .env${NC}"
    else
        echo -e "${YELLOW}⚠️  CRON_INTERVAL_MINUTES not found in .env, using default: 15 minutes${NC}"
    fi
else
    echo -e "${RED}❌ .env file not found, using default: 15 minutes${NC}"
fi

# Get current directory
INSTALL_DIR=$(pwd)

# Remove old cron entries
echo -e "${YELLOW}🗑️  Removing old cron entries...${NC}"
crontab -l 2>/dev/null | grep -v "run_cron_job.sh" | crontab -

# Add new cron entry
echo -e "${YELLOW}➕ Adding new cron entry...${NC}"
# run_cron_job.sh already tees into logs/cron.log, so discard cron's own copy
# instead of writing every line twice (and filling root's mail spool).
mkdir -p "$INSTALL_DIR/logs"
CRON_ENTRY="*/$CRON_INTERVAL * * * * cd $INSTALL_DIR && ./run_cron_job.sh > /dev/null 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo -e "${GREEN}✅ Cron interval updated successfully!${NC}"
echo -e "${GREEN}📅 New schedule: Every $CRON_INTERVAL minutes${NC}"
echo ""
echo -e "${YELLOW}📋 Verify with:${NC} crontab -l"
echo -e "${YELLOW}📊 Monitor logs:${NC} tail -f logs/cron.log"
