#!/bin/bash

API_KEY='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkMWJhNThjMDliNzY0Y2EzOWE3Y2RkOWUwNmQyMjJlZCIsImlhdCI6MTU4ODIzNzk3NCwiZXhwIjoxOTAzNTk3OTc0fQ.guPWqoD6VOQb3v6bYNfWhd9IDw6vw7Ys0F4XwHdI3TY';

set -x

curl -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${2}" \
    "http://localhost:8123/api/services/homeassistant/restart"

