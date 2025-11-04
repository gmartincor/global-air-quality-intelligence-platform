#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================="
echo "Environment Verification Script"
echo "================================="
echo ""

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is not installed"
        return 1
    fi
}

check_docker_running() {
    if docker info &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker daemon is running"
        return 0
    else
        echo -e "${RED}✗${NC} Docker daemon is not running"
        return 1
    fi
}

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} Port $1 is already in use"
        return 1
    else
        echo -e "${GREEN}✓${NC} Port $1 is available"
        return 0
    fi
}

check_docker_image() {
    if docker images | grep -q "$1"; then
        echo -e "${GREEN}✓${NC} Docker image $1 exists"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Docker image $1 not found (run 'make dev-build')"
        return 1
    fi
}

check_docker_containers() {
    local running=$(docker ps --filter "name=air-quality" --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$running" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} $running air-quality containers are running"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} No air-quality containers are running (run 'make up')"
        return 1
    fi
}

echo "Checking prerequisites..."
echo ""

ERRORS=0

check_command docker || ERRORS=$((ERRORS+1))
check_command make || ERRORS=$((ERRORS+1))
check_command git || ERRORS=$((ERRORS+1))

echo ""
echo "Checking Docker..."
echo ""

check_docker_running || ERRORS=$((ERRORS+1))

echo ""
echo "Checking ports..."
echo ""

check_port 8080
check_port 8081
check_port 4566
check_port 5432
check_port 6379

echo ""
echo "Checking Docker images..."
echo ""

check_docker_image "air-quality-dev"

echo ""
echo "Checking running containers..."
echo ""

check_docker_containers

echo ""
echo "Checking project files..."
echo ""

if [ -f "Makefile" ]; then
    echo -e "${GREEN}✓${NC} Makefile exists"
else
    echo -e "${RED}✗${NC} Makefile not found"
    ERRORS=$((ERRORS+1))
fi

if [ -f "infrastructure/docker/docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} docker-compose.yml exists"
else
    echo -e "${RED}✗${NC} docker-compose.yml not found"
    ERRORS=$((ERRORS+1))
fi

if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml exists"
else
    echo -e "${RED}✗${NC} pyproject.toml not found"
    ERRORS=$((ERRORS+1))
fi

echo ""
echo "================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo ""
    echo "You can now:"
    echo "  1. Run 'make dev-build' to build containers (if not done)"
    echo "  2. Run 'make up' to start all services"
    echo "  3. Run 'make dev-shell' to enter development environment"
    echo "  4. Run 'make help' to see all commands"
else
    echo -e "${RED}Found $ERRORS issue(s)${NC}"
    echo ""
    echo "Please fix the issues above and run this script again."
    echo ""
    echo "Common fixes:"
    echo "  - Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    echo "  - Start Docker Desktop"
    echo "  - Run 'make dev-build' to build images"
    echo "  - Run 'make up' to start services"
    echo "  - Check if ports are free: 8080, 8081, 4566, 5432, 6379"
fi

echo "================================="

exit $ERRORS
