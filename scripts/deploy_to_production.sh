#!/bin/bash
################################################################################
# Complete Production Deployment Script
#
# This script does EVERYTHING needed to go from 98% to 100% production ready:
# 1. Checks prerequisites
# 2. Sets up environment
# 3. Starts all services
# 4. Runs comprehensive tests
# 5. Validates results
# 6. Provides deployment summary
#
# Usage:
#   ./scripts/deploy_to_production.sh
#
# What it does:
#   - Validates environment
#   - Generates production tokens (if needed)
#   - Starts Docker containers
#   - Waits for services to be ready
#   - Runs all 30+ tests
#   - Shows final deployment status
################################################################################

set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SKIP_TESTS=${SKIP_TESTS:-false}
AUTO_FIX=${AUTO_FIX:-true}

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

################################################################################
# Step 1: Check Prerequisites
################################################################################

check_prerequisites() {
    print_header "Step 1: Checking Prerequisites"

    local all_good=true

    # Check Docker
    print_step "Checking Docker..."
    if command -v docker &> /dev/null; then
        if docker ps &> /dev/null; then
            print_success "Docker is installed and running"
        else
            print_error "Docker is installed but not running"
            echo "  Start Docker: sudo systemctl start docker"
            all_good=false
        fi
    else
        print_error "Docker is not installed"
        echo "  Install: https://docs.docker.com/get-docker/"
        all_good=false
    fi

    # Check docker-compose
    print_step "Checking docker-compose..."
    if command -v docker-compose &> /dev/null; then
        print_success "docker-compose is installed"
    else
        print_error "docker-compose is not installed"
        echo "  Install: sudo apt-get install docker-compose"
        all_good=false
    fi

    # Check jq
    print_step "Checking jq..."
    if command -v jq &> /dev/null; then
        print_success "jq is installed"
    else
        print_error "jq is not installed"
        echo "  Install: sudo apt-get install jq"
        all_good=false
    fi

    # Check curl
    print_step "Checking curl..."
    if command -v curl &> /dev/null; then
        print_success "curl is installed"
    else
        print_error "curl is not installed"
        echo "  Install: sudo apt-get install curl"
        all_good=false
    fi

    # Check files exist
    print_step "Checking required files..."
    if [ -f "docker-compose.yml" ]; then
        print_success "docker-compose.yml exists"
    else
        print_error "docker-compose.yml not found"
        all_good=false
    fi

    if [ -f ".env.example" ]; then
        print_success ".env.example exists"
    else
        print_error ".env.example not found"
        all_good=false
    fi

    if ! $all_good; then
        echo ""
        print_error "Prerequisites check FAILED"
        echo "  Please install missing dependencies and try again"
        exit 1
    fi

    echo ""
    print_success "All prerequisites met!"
}

################################################################################
# Step 2: Setup Environment
################################################################################

setup_environment() {
    print_header "Step 2: Setting Up Environment"

    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found"

        if [ "$AUTO_FIX" = "true" ]; then
            print_step "Creating .env from .env.example..."
            cp .env.example .env
            print_success ".env file created"

            print_warning "Please review .env and update with your values:"
            echo "  - SMTP credentials"
            echo "  - SendGrid/Mailgun API keys (if using)"
            echo "  - Production service tokens"
            echo ""
            read -p "Press ENTER when ready to continue..."
        else
            print_error "Please create .env file from .env.example"
            exit 1
        fi
    else
        print_success ".env file exists"
    fi

    # Check critical env vars
    print_step "Checking .env configuration..."

    if grep -q "SERVICE_AUTH_ENABLED=true" .env; then
        print_success "Service authentication is enabled"
    else
        print_warning "SERVICE_AUTH_ENABLED not set to true"
    fi

    if grep -q "SERVICE_TOKEN_MAIN_APP=st_" .env; then
        print_success "Service token configured"
    else
        print_warning "SERVICE_TOKEN_MAIN_APP may need to be set"
    fi

    echo ""
    print_success "Environment setup complete!"
}

################################################################################
# Step 3: Start Services
################################################################################

start_services() {
    print_header "Step 3: Starting Docker Services"

    # Stop any existing containers
    print_step "Stopping existing containers (if any)..."
    docker-compose down &> /dev/null || true
    print_success "Clean slate ready"

    # Build images
    print_step "Building Docker images..."
    if docker-compose build; then
        print_success "Docker images built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi

    # Start containers
    print_step "Starting containers..."
    if docker-compose up -d; then
        print_success "Containers started"
    else
        print_error "Failed to start containers"
        docker-compose logs
        exit 1
    fi

    # Show running containers
    print_step "Checking container status..."
    echo ""
    docker-compose ps
    echo ""

    # Wait for services to be ready
    print_step "Waiting for services to be ready (30 seconds)..."
    for i in {1..30}; do
        echo -n "."
        sleep 1
    done
    echo ""
    print_success "Services should be ready"

    # Quick health check
    print_step "Testing health endpoint..."
    if curl -sf http://localhost:8010/health > /dev/null; then
        print_success "Health endpoint responding!"
    else
        print_warning "Health endpoint not responding yet (may need more time)"
    fi

    echo ""
    print_success "All services started!"
}

################################################################################
# Step 4: Run Tests
################################################################################

run_tests() {
    print_header "Step 4: Running Comprehensive Tests"

    if [ "$SKIP_TESTS" = "true" ]; then
        print_warning "Tests skipped (SKIP_TESTS=true)"
        return 0
    fi

    print_step "Running test suite..."
    echo ""

    if ./scripts/test_email_service.sh; then
        echo ""
        print_success "ALL TESTS PASSED! ✓✓✓"
        return 0
    else
        echo ""
        print_error "Some tests failed"
        return 1
    fi
}

################################################################################
# Step 5: Deployment Summary
################################################################################

show_summary() {
    local tests_passed=$1

    print_header "Deployment Summary"

    echo -e "${BOLD}Services Status:${NC}"
    docker-compose ps
    echo ""

    echo -e "${BOLD}Access URLs:${NC}"
    echo "  Email API:       http://localhost:8010"
    echo "  Health Check:    http://localhost:8010/health"
    echo "  Monitor Dashboard: http://localhost:8011"
    echo "  MailHog UI:      http://localhost:8025"
    echo ""

    echo -e "${BOLD}Service Tokens:${NC}"
    echo "  Main App:        $(grep SERVICE_TOKEN_MAIN_APP .env | cut -d= -f2 | head -c 30)..."
    echo ""

    if [ $tests_passed -eq 0 ]; then
        echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}${BOLD}  ✓✓✓ PRODUCTION READY - 100% ✓✓✓${NC}"
        echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${GREEN}All systems operational!${NC}"
        echo "Your email service is ready for production deployment."
        echo ""
        echo "Next steps:"
        echo "  1. Review logs: docker-compose logs"
        echo "  2. Send a test email"
        echo "  3. Check monitoring dashboard"
        echo "  4. Deploy to production environment"
    else
        echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}${BOLD}  ⚠ TESTS FAILED - NEEDS ATTENTION ⚠${NC}"
        echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "Some tests failed. Please:"
        echo "  1. Check logs: docker-compose logs"
        echo "  2. Review test output above"
        echo "  3. Check docs/TEST_TROUBLESHOOTING.md"
        echo "  4. Fix issues and re-run this script"
    fi

    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    clear

    cat << "EOF"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FreeFace Email Service - Production Deployment

  This will:
  ✓ Check all prerequisites
  ✓ Setup environment (.env)
  ✓ Start all Docker services
  ✓ Run comprehensive tests (30+)
  ✓ Validate production readiness

  Time: ~3-5 minutes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

    echo ""
    read -p "Ready to proceed? (y/N) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi

    # Run all steps
    check_prerequisites
    setup_environment
    start_services

    tests_passed=0
    if run_tests; then
        tests_passed=0  # Success
    else
        tests_passed=1  # Failure
    fi

    show_summary $tests_passed

    exit $tests_passed
}

# Run main
main "$@"
