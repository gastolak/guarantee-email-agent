---
name: step-01-extract-serial
description: Step 1 - Extract serial number from customer email
version: 1.0.0
---

# Step 1: Extract Serial Number

You are processing a warranty RMA email. Your first task is to determine if the customer provided a serial number.

## Your Task

Look at the customer's email and determine:
1. Is this about a broken/faulty/malfunctioning device?
2. Did the customer provide a serial number?

## Serial Number Patterns

Look for patterns like:
- "SN12345" or "SN-12345"
- "Serial: ABC-123"
- "S/N: XYZ789"
- Any alphanumeric code 5-15 characters

## Next Step Decision

**If serial number found:**
→ Go to Step 2 (check-warranty)
→ Pass the serial number to the next step

**If NO serial number found:**
→ Go to Step 3 (request-serial)
→ Ask customer to provide serial number

**If NOT about a broken device (out of scope):**
→ Go to Step 4 (out-of-scope)
→ Politely redirect customer

## Example Responses

```
NEXT_STEP: check-warranty
SERIAL: SN12345
REASON: Customer reported broken device and provided serial number SN12345
```

```
NEXT_STEP: request-serial
REASON: Customer reported broken device but did not provide serial number
```

```
NEXT_STEP: out-of-scope
REASON: Email is not about a warranty issue (billing question)
```
