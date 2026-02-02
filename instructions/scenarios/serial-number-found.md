---
name: serial-number-found
description: Serial number was successfully extracted - next step is to check warranty status
version: 1.0.0
---

# Serial Number Found - Check Warranty Status

You have successfully extracted a serial number from the customer's email about a broken/faulty device.

## Next Step

**Call the `check_warranty` function with the serial number to determine if the warranty is valid.**

### Function to Call

```
check_warranty(serial_number: str)
```

**Example:**
- If serial number is "SN12345", call: `check_warranty("SN12345")`

### After Getting Warranty Status

Based on the warranty check result:

1. **If warranty is VALID (active, not expired)**:
   - Go to `valid-warranty` scenario
   - Create a support ticket
   - Send confirmation email to customer

2. **If warranty is INVALID (expired, device not found, or not covered)**:
   - Go to `invalid-warranty` scenario
   - Send polite email explaining the issue
   - Offer paid repair options if applicable

3. **If warranty check fails (API error, network issue)**:
   - Go to `graceful-degradation` scenario
   - Apologize and ask customer to contact support directly

## Important Notes

- **Always call `check_warranty` first** before deciding on the scenario
- **Do not assume** warranty status without checking the API
- The warranty check will tell you if the device exists in the system and if warranty is active
- Handle all edge cases gracefully (device not found, warranty expired, etc.)
