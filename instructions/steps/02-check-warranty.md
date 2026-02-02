---
name: step-02-check-warranty
description: Step 2 - Check warranty status by calling API
version: 1.0.0
---

# Step 2: Check Warranty Status

You have a serial number. Now you must check if the warranty is valid.

## Your Task

**Call the `check_warranty` function with the serial number.**

Example:
```
check_warranty(serial_number="SN12345")
```

## Wait for Response

After calling `check_warranty`, you will receive one of these responses:

### Response 1: Valid Warranty
```json
{
  "serial_number": "SN12345",
  "status": "valid",
  "expiration_date": "2025-12-31",
  "customer_name": "Jan Kowalski"
}
```
→ **NEXT_STEP: valid-warranty** (Step 3a)
→ Warranty is active, proceed to create ticket

### Response 2: Expired Warranty
```json
{
  "serial_number": "SN12345",
  "status": "expired",
  "expiration_date": "2023-01-15"
}
```
→ **NEXT_STEP: expired-warranty** (Step 3b)
→ Warranty expired, offer paid repair

### Response 3: Device Not Found
```json
{
  "error": "Device not found",
  "serial_number": "asdfadsf"
}
```
→ **NEXT_STEP: device-not-found** (Step 3c)
→ Serial not in system, ask for correct serial

### Response 4: API Error
```json
{
  "error": "Connection timeout"
}
```
→ **NEXT_STEP: api-error** (Step 3d)
→ System error, ask customer to contact support

## Important

- **ALWAYS call `check_warranty` first** - never assume warranty status
- **Wait for the API response** before deciding next step
- The API response determines which step to execute next
