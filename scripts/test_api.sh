#!/bin/bash
  BASE_URL="http://localhost:3570/api"

  # Login with wrong password
  echo "=== Login ==="
  RESP=$(curl -s -X POST $BASE_URL/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"ABC","password":"xuuuuuuu"}')
  TOKEN=$(echo $RESP | jq -r '.access_token')
  echo "With wrong password Token: $TOKEN"

  # Login
  echo "=== Login ==="
  RESP=$(curl -s -X POST $BASE_URL/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"ABC","password":"uuuuuuuu"}')
  TOKEN=$(echo $RESP | jq -r '.access_token')
  echo "Token: $TOKEN"

  # Send SMS
  echo ""
  echo "=== Send SMS ==="
  curl -s -X POST $BASE_URL/sms \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"recipient":"85212345678","content":"Test message"}' | jq

  # List messages
  echo ""
  echo "=== List Messages ==="
  curl -s $BASE_URL/sms \
    -H "Authorization: Bearer $TOKEN" | jq

