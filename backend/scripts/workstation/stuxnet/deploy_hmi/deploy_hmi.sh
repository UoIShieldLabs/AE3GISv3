#!/bin/bash

# Example Usage: ./deploy_hmi.sh "[HMI_IP_ADDRESS and PORT]/ScadaBR"
# NOTE: You may need to change the IP Address for the Modbus data point in motor_hmi.json. That value is currently hardcoded.

# HMI_URL="172.16.101.30:8080/ScadaBR"
HMI_URL=${1:-}
if [[ -z "$HMI_URL" ]]; then
    echo "Usage: $0 \"[HMI_IP_ADDRESS and PORT]/ScadaBR\""
    exit 1
fi

if [[ ! "$HMI_URL" =~ ^https?:// ]]; then
    HMI_URL="http://$HMI_URL"
fi
HMI_URL="${HMI_URL%/}"
if [[ "$HMI_URL" != */ScadaBR ]]; then
    HMI_URL="$HMI_URL/ScadaBR"
fi

HMI_USERNAME="admin"
HMI_PASSWORD="admin"
COOKIE_JAR="$(mktemp /tmp/hmi_cookie.XXXXXX)"
trap 'rm -f "$COOKIE_JAR"' EXIT
CONFIG_FILE="motor_hmi.json"

# Login and get session cookie
echo "Login..."
LOGIN_RESPONSE=$(curl -sSL -c "$COOKIE_JAR" \
     -X POST "$HMI_URL/login.htm" \
     -d "username=$HMI_USERNAME&password=$HMI_PASSWORD")

# Validate login by requesting the protected HMI homepage
HOME_PAGE=$(curl -sSL -b "$COOKIE_JAR" "$HMI_URL")
if ! printf '%s\n' "$HOME_PAGE" | grep -qi "ScadaBR"; then
    echo "ERROR: login failed"
    printf '%s\n' "$HOME_PAGE" | head -60
    exit 1
fi

# Get scriptSessionId Token
echo "Get DWR session token..."
DWR_ENGINE_RESPONSE=$(curl -sSL -b "$COOKIE_JAR" "$HMI_URL/dwr/engine.js")
DWR_ENGINE_REGEX='dwr\.engine\._origScriptSessionId = "([^"]*)";'
if [[ "$DWR_ENGINE_RESPONSE" =~ $DWR_ENGINE_REGEX ]]; then
    ORIG_TOKEN="${BASH_REMATCH[1]}"
else
    echo "ERROR: could not extract DWR session token"
    printf '%s\n' "$DWR_ENGINE_RESPONSE" | head -40
    exit 1
fi

# Append the random suffix to complete DWR scriptSessionId Token
RAND_SUFFIX=$(printf "%03d" $((RANDOM % 1000)))
SCRIPT_SESSION_ID="$ORIG_TOKEN$RAND_SUFFIX"


# URL Encode the JSON Config File and push to ScadaBR
echo "Encode config file and push config to ScadaBR..."
ENCODED_JSON=$(python3 -c "
import json, urllib.parse, sys
try:
    with open('$CONFIG_FILE','r') as f:
        data = json.load(f)
        minified = json.dumps(data, separators=(',', ':'))
        print(urllib.parse.quote(minified))
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

if [[ $? -ne 0 ]]; then
    echo "Error: Python falied to process config file: $CONFIG_FILE"
    exit 1
fi

PAYLOAD="callCount=1
page=/ScadaBR/emport.shtm
httpSessionId=
scriptSessionId=$SCRIPT_SESSION_ID
c0-scriptName=EmportDwr
c0-methodName=importData
c0-id=0
c0-param0=string:$ENCODED_JSON"

echo "Push config to ScadaBR..."
UPLOAD_RESPONSE=$(curl -sSL -b "$COOKIE_JAR" \
     -H "Content-Type: text/plain;charset=UTF-8" \
     -H "Accept: */*" \
     -X POST "$HMI_URL/dwr/call/plaincall/EmportDwr.importData.dwr" \
     --data-binary "$PAYLOAD")

if [[ -z "$UPLOAD_RESPONSE" ]]; then
    echo "ERROR: no response from ScadaBR import endpoint"
    exit 1
fi

echo "Upload response:"
printf '%s\n' "$UPLOAD_RESPONSE" | head -40
if echo "$UPLOAD_RESPONSE" | grep -qi "exception\|error\|fail"; then
    echo "ERROR: ScadaBR import failed"
    exit 1
fi

  