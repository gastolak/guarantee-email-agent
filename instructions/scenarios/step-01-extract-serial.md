---
name: step-01-extract-serial
description: Step 1 - Analyze email and extract serial number
trigger: step-01-extract-serial
version: 1.0.0
---

<objective>
Step 01: Extract Serial Number

This is the ENTRY POINT for all warranty emails.

Analyze the customer's email to determine:
1. Is this a warranty-related inquiry?
2. Does the customer provide a serial number?
3. What is the next step in the workflow?

NOTE: Serial extraction is handled by serial_extractor.py (automated).
This scenario file defines the decision logic for routing after extraction.
</objective>

<serial-number-patterns>
Recognize serial numbers in these common formats:
- "SN12345" or "SN-12345" (with or without hyphen)
- "Serial: ABC-123" or "Serial Number: ABC-123"
- "S/N: XYZ789" or "S/N XYZ789"
- "Serial #1234567890" or "#1234567890"
- Alphanumeric sequences 5-20 characters
- May include hyphens, spaces, or special characters

If multiple serial numbers present:
- Use the first/primary serial number
- Flag as ambiguous if unclear which is primary
</serial-number-patterns>

<routing-logic>
Based on email analysis, route to the appropriate next step:

**Case 1: Serial Found + Warranty Issue**
- Email mentions device problem (broken, faulty, not working, malfunction, RMA, defective, failed, error)
- Serial number extracted successfully
- → NEXT STEP: step-02-check-warranty

**Case 2: No Serial + Warranty Issue**
- Email mentions device problem
- No serial number found
- → NEXT STEP: step-03d-request-serial

**Case 3: Out of Scope**
- Email is NOT about warranty (billing, sales, general support, spam)
- → NEXT STEP: step-04-out-of-scope
</routing-logic>

<warranty-keywords>
Keywords indicating warranty issue:
- broken, faulty, not working, malfunction
- RMA, defective, failed, error, problem
- repair, warranty, guarantee
- stopped working, won't boot, won't start
- emergency mode, crash, freeze
</warranty-keywords>

<decision-tree>
```
Is this a warranty-related email?
├─ YES: Does it contain a serial number?
│   ├─ YES: → step-02-check-warranty
│   └─ NO:  → step-03d-request-serial
└─ NO:  → step-04-out-of-scope
```
</decision-tree>

<important>
- This is the ENTRY POINT - every email starts here
- Serial extraction is automated by serial_extractor.py
- This scenario defines the routing logic after extraction
- Do NOT send emails in this step - only analyze and route
</important>
