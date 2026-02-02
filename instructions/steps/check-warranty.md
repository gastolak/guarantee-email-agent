---
name: step-02-check-warranty
description: Step 2 - Check warranty status by calling API
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

## Output Format

After receiving the warranty response, you **MUST** output:

```
NEXT_STEP: <step-name>
```

Where `<step-name>` is:
- `valid-warranty` if status is "valid"
- `expired-warranty` if status is "expired"
- `device-not-found` if error is "Device not found"
- `api-error` for other errors
