#!/bin/bash
set -euo pipefail

# PLC_URL="http://172.16.101.10:8080"
PLC_URL=${1:-}
if [[ -z "$PLC_URL" ]]; then
    echo "Usage: $0 <PLC_URL>"
    echo "Example: $0 http://192.168.1.6:8080"
    exit 1
fi

if [[ ! "$PLC_URL" =~ ^https?:// ]]; then
    PLC_URL="http://$PLC_URL"
fi

PLC_USERNAME="openplc"
PLC_PASSWORD="openplc"
COOKIE_JAR="$(mktemp /tmp/plc_cookie.XXXXXX)"
trap 'rm -f "$COOKIE_JAR"' EXIT
MOTOR_ST_FILE="motor.st"
MOTOR_PSM_FILE="motor_psm.py"
MOTOR_PROGRAM_NAME="motor_test"

extract_csrf_token() {
    local html="$1"
    printf '%s\n' "$html" | grep -o -E "name=['\"]csrf_token['\"][^>]*value=['\"][^'\"]*['\"]|value=['\"][^'\"]*['\"][^>]*name=['\"]csrf_token['\"]" | head -n1 | sed -E "s/.*value=['\"]([^'\"]*)['\"].*/\1/" || true
}

# Fetch login page for CSRF token
echo "Login..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "$PLC_URL/login")

CSRF_TOKEN=$(extract_csrf_token "$LOGIN_PAGE")

if [[ -z "$CSRF_TOKEN" ]]; then
    echo "ERROR: Could not extract CSRF token from login page"
    echo "First 50 lines of login page:"
    printf '%s\n' "$LOGIN_PAGE" | head -50
    exit 1
fi

CSRF_TOKEN_LOGIN="$CSRF_TOKEN"

LOGIN_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
     -X POST "$PLC_URL/login" \
     -H "X-CSRFToken: $CSRF_TOKEN" \
     -d "username=$PLC_USERNAME&password=$PLC_PASSWORD&csrf_token=$CSRF_TOKEN")

if echo "$LOGIN_RESPONSE" | grep -q -i "Bad Request\|missing\|error\|csrf"; then
    echo "ERROR: Login failed"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "Change HW Layer..."
HW_PAGE=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/hardware")
CSRF_TOKEN=$(extract_csrf_token "$HW_PAGE")
if [[ -z "$CSRF_TOKEN" ]]; then
    echo "WARNING: could not extract CSRF token from hardware page, using login token"
    CSRF_TOKEN="$CSRF_TOKEN_LOGIN"
fi

HW_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -X POST "$PLC_URL/hardware" \
        -H "Referer: $PLC_URL/hardware" \
        -F "hardware_layer=psm_linux" \
        -F "csrf_token=$CSRF_TOKEN" \
        -F "custom_layer_code=<$MOTOR_PSM_FILE")

if echo "$HW_RESPONSE" | grep -qi "error\|bad request\|failed\|missing\|csrf"; then
    echo "ERROR: hardware layer update failed"
    printf '%s\n' "$HW_RESPONSE"
    exit 1
fi

# Get upload-program CSRF token
UPLOAD_PAGE=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/upload-program")
UPLOAD_CSRF_TOKEN=$(extract_csrf_token "$UPLOAD_PAGE")
if [[ -z "$UPLOAD_CSRF_TOKEN" ]]; then
    echo "WARNING: could not extract upload CSRF token from upload-program page, using login token"
    UPLOAD_CSRF_TOKEN="$CSRF_TOKEN_LOGIN"
fi

# Upload and compile ST file
echo "Upload File..."
UPLOAD_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -X POST "$PLC_URL/upload-program" \
        -H "Referer: $PLC_URL/upload-program" \
        -H "X-CSRFToken: $UPLOAD_CSRF_TOKEN" \
        -F "csrf_token=$UPLOAD_CSRF_TOKEN" \
        -F "file=@$MOTOR_ST_FILE" \
        -F "name=$MOTOR_PROGRAM_NAME")

MATCH_FILE=$(printf '%s\n' "$UPLOAD_RESPONSE" | sed -n "s/.*value=[\"']\([0-9]\+\.st\)[\"'].*/\1/p" | head -n1)
if [[ -z "$MATCH_FILE" ]]; then
    echo "PATTERN not found: upload file name"
    printf '%s\n' "$UPLOAD_RESPONSE"
    exit 1
fi

MATCH_TIME=$(printf '%s\n' "$UPLOAD_RESPONSE" | sed -n "s/.*id=[\"'][^\"']*[\"'].*value=[\"']\([0-9]\+\)[\"'].*/\1/p" | head -n1)
if [[ -z "$MATCH_TIME" ]]; then
    echo "PATTERN not found: epoch time"
    printf '%s\n' "$UPLOAD_RESPONSE"
    exit 1
fi

echo "Upload File Action..."
curl -s -b "$COOKIE_JAR" \
        -X POST "$PLC_URL/upload-program-action" \
        -H "Referer: $PLC_URL/upload-program-action" \
        -H "X-CSRFToken: $UPLOAD_CSRF_TOKEN" \
        -F "csrf_token=$UPLOAD_CSRF_TOKEN" \
        -F "prog_name=$MOTOR_PROGRAM_NAME" \
        -F "prog_descr=''" \
        -F "prog_file=$MATCH_FILE" \
        -F "epoch_time=$MATCH_TIME" > /dev/null

echo "Compile..."
curl -s -b "$COOKIE_JAR" \
     -X GET "$PLC_URL/compile-program?file=$MATCH_FILE" > /dev/null

COMPILE_LOGS=""
COMPILE_REGEX="Compilation finished"
while ! [[ "$COMPILE_LOGS" =~ $COMPILE_REGEX ]]; do
    COMPILE_LOGS=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/compilation-logs")
    sleep 1
done

echo "Start..."
curl -s -b "$COOKIE_JAR" \
        -X GET "$PLC_URL/start_plc" > /dev/null

echo "Deployment complete!"
