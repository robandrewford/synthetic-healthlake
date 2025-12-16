#!/usr/bin/env bash
# Security scanning script for local development
# Runs all security tools configured in the project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create reports directory
REPORT_DIR="./security-reports"
mkdir -p "$REPORT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Synthetic HealthLake Security Scan${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}>>> $1${NC}\n"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Track overall status
ERRORS=0
WARNINGS=0

# Check if running in project root
if [ ! -f "pyproject.toml" ]; then
    print_error "Must be run from project root directory"
    exit 1
fi

# 1. Python Dependencies - pip-audit
print_section "1. Python Dependencies (pip-audit)"
if command -v pip-audit &> /dev/null; then
    if pip-audit --desc 2>&1 | tee "$REPORT_DIR/pip-audit.txt"; then
        print_success "No vulnerabilities found in Python dependencies"
    else
        print_error "Vulnerabilities found in Python dependencies"
        ERRORS=$((ERRORS + 1))
    fi

    # Generate JSON report
    pip-audit --format json --output "$REPORT_DIR/pip-audit.json" 2>/dev/null || true
else
    print_warning "pip-audit not installed. Run: uv pip install pip-audit"
    WARNINGS=$((WARNINGS + 1))
fi

# 2. Python Security - Safety
print_section "2. Python Security (Safety)"
if command -v safety &> /dev/null; then
    if safety check 2>&1 | tee "$REPORT_DIR/safety.txt"; then
        print_success "No known security vulnerabilities found"
    else
        print_warning "Safety check found issues (may include false positives)"
        WARNINGS=$((WARNINGS + 1))
    fi

    # Generate JSON report
    safety check --json --output "$REPORT_DIR/safety.json" 2>/dev/null || true
else
    print_warning "safety not installed. Run: uv pip install safety"
    WARNINGS=$((WARNINGS + 1))
fi

# 3. Python Code Security - Bandit
print_section "3. Python Code Security (Bandit)"
if command -v bandit &> /dev/null; then
    if bandit -r health_platform/ synthetic/ -f screen 2>&1 | tee "$REPORT_DIR/bandit.txt"; then
        print_success "No security issues found in Python code"
    else
        print_warning "Bandit found potential security issues"
        WARNINGS=$((WARNINGS + 1))
    fi

    # Generate JSON report
    bandit -r health_platform/ synthetic/ -f json -o "$REPORT_DIR/bandit.json" 2>/dev/null || true
else
    print_warning "bandit not installed. Run: uv pip install bandit"
    WARNINGS=$((WARNINGS + 1))
fi

# 4. Node.js Dependencies - npm audit
print_section "4. Node.js Dependencies (npm audit)"
if [ -d "cdk" ] && [ -f "cdk/package.json" ]; then
    cd cdk
    if npm audit --audit-level=moderate 2>&1 | tee "../$REPORT_DIR/npm-audit.txt"; then
        print_success "No moderate or higher vulnerabilities in Node.js dependencies"
    else
        print_error "Vulnerabilities found in Node.js dependencies"
        ERRORS=$((ERRORS + 1))
    fi

    # Generate JSON report
    npm audit --json > "../$REPORT_DIR/npm-audit.json" 2>/dev/null || true
    cd ..
else
    print_warning "CDK directory not found, skipping npm audit"
fi

# 5. Container/Filesystem - Trivy (if installed)
print_section "5. Filesystem Security (Trivy)"
if command -v trivy &> /dev/null; then
    if trivy fs --severity HIGH,CRITICAL --exit-code 1 . 2>&1 | tee "$REPORT_DIR/trivy.txt"; then
        print_success "No high or critical vulnerabilities found"
    else
        print_error "Trivy found vulnerabilities"
        ERRORS=$((ERRORS + 1))
    fi

    # Generate JSON report
    trivy fs --format json --output "$REPORT_DIR/trivy.json" . 2>/dev/null || true
else
    print_warning "trivy not installed. Install with: brew install aquasecurity/trivy/trivy"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. Pre-commit Hooks
print_section "6. Pre-commit Security Hooks"
if command -v pre-commit &> /dev/null; then
    if pre-commit run --all-files 2>&1 | tee "$REPORT_DIR/pre-commit.txt"; then
        print_success "All pre-commit hooks passed"
    else
        print_warning "Some pre-commit hooks failed"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    print_warning "pre-commit not installed. Run: uv pip install pre-commit"
    WARNINGS=$((WARNINGS + 1))
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Security Scan Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Reports saved to: ${BLUE}$REPORT_DIR/${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All security checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Scan completed with $WARNINGS warnings${NC}"
    echo "Review the reports in $REPORT_DIR/ for details"
    exit 0
else
    echo -e "${RED}✗ Scan found $ERRORS critical issues and $WARNINGS warnings${NC}"
    echo "Review the reports in $REPORT_DIR/ for details"
    exit 1
fi
