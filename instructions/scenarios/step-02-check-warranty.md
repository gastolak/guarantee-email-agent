---
name: step-02-check-warranty
description: Step 2 - Check warranty status by calling API
trigger: step-02-check-warranty
version: 1.0.0
available_functions:
  - name: check_warranty
    description: Check warranty status for a product serial number. Returns warranty validity, expiration date, and coverage details.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number to check warranty status for
      required: [serial_number]
---

<objective>
Step 2: Check Warranty Status

You have a serial number from the customer's email. Your task is to check if the warranty is valid by calling the warranty API.

WORKFLOW:
1. Call check_warranty(serial_number) with the extracted serial number
2. Wait for API response
3. Based on the response, route to the appropriate next step

This is a DECISION POINT step - the API response determines which step comes next.
</objective>

<instructions>
Call check_warranty with the serial number:

Example:
```
check_warranty(serial_number="SN12345")
```

Wait for one of these responses:

**Response 1: Valid Warranty**
```json
{
  "serial_number": "SN12345",
  "status": "valid",
  "expiration_date": "2025-12-31",
  "customer_name": "Jan Kowalski"
}
```
→ NEXT STEP: step-03a-valid-warranty (create ticket)

**Response 2: Expired Warranty**
```json
{
  "serial_number": "SN12345",
  "status": "expired",
  "expiration_date": "2023-01-15"
}
```
→ NEXT STEP: step-03c-expired-warranty (offer paid repair)

**Response 3: Device Not Found**
```json
{
  "error": "Device not found",
  "serial_number": "SN12345"
}
```
→ NEXT STEP: step-03b-device-not-found (ask to verify serial)

**Response 4: API Error**
```json
{
  "error": "Connection timeout"
}
```
→ NEXT STEP: step-04-out-of-scope (apologize, ask to contact support)
</instructions>

<routing-logic>
Based on check_warranty response:
- status="valid" → step-03a-valid-warranty
- status="expired" → step-03c-expired-warranty
- error="Device not found" → step-03b-device-not-found
- error=(any other) → step-04-out-of-scope
</routing-logic>

<important>
- ALWAYS call check_warranty first - never assume warranty status
- Wait for the API response before deciding next step
- The API response determines the routing
- Do NOT send any emails in this step - only check warranty
</important>
