---
name: main-orchestration
description: Main orchestration instruction for warranty email processing
version: 1.0.0
---

<objective>
Process warranty RMA emails for broken/faulty devices by extracting serial numbers, validating warranty status, and creating support tickets for valid warranty claims.
</objective>

<workflow>
Follow this workflow for every email:
1. Check if email reports a broken/faulty/malfunctioning device
2. Extract serial number using the patterns defined below
3. Determine scenario:
   - Serial number present + device issue = valid-warranty (check warranty API)
   - No serial number + device issue = missing-info (request serial)
   - No device issue = graceful-degradation (out of scope)
4. Return structured output with scenario, serial number, and confidence

**Typical RMA Flow:**
- Customer reports broken device with serial → validate warranty → create ticket if valid
- Customer reports broken device without serial → ask for serial number
- Warranty expired → offer paid repair option
- Not warranty-related → politely redirect to appropriate channel
</workflow>

<serial-number-patterns>
Recognize serial numbers in these common formats:
- "SN12345" or "SN-12345" (with or without hyphen)
- "Serial: ABC-123" or "Serial Number: ABC-123"
- "S/N: XYZ789" or "S/N XYZ789"
- "Serial #1234567890" or "#1234567890"
- Alphanumeric sequences 5-20 characters
- May include hyphens, spaces, or special characters

If multiple serial numbers present:
- Log all found serial numbers
- Return the first/primary serial number
- Flag as ambiguous if unclear which is primary
</serial-number-patterns>

<scenario-detection>
Identify the appropriate scenario based on email characteristics:

**valid-warranty**:
- Email contains a clear serial number
- Device is reported as broken, not working, or has issues (RMA request)
- Customer wants warranty service/repair/replacement
- This is the PRIMARY scenario when serial number is present

**invalid-warranty**:
- Email contains serial number
- Device has issues but warranty validation will fail (expired/not covered)
- Use this only after warranty API confirms invalid warranty status

**missing-info**:
- No serial number found in email body
- Serial number is ambiguous or unclear
- Multiple serial numbers without clear primary
- Device issue mentioned but no serial provided

**graceful-degradation**:
- Email is not about warranty (billing, general support, etc.)
- Spam or unrelated inquiry
- No device/warranty-related keywords present
- Unable to determine intent clearly

**Key Rule**: If email mentions broken/faulty device AND contains serial number → **valid-warranty**
Intent doesn't need to explicitly ask about warranty status - reporting a broken device IS a warranty request.

Default to **missing-info** if device issue mentioned but no serial number found.
</scenario-detection>

<analysis-guidelines>
- **Primary trigger**: Device reported as broken/faulty/not working + serial number = valid-warranty
- If serial number is present, assume it's a warranty RMA request (don't require explicit "warranty" mention)
- Extract exact serial number text, preserve formatting
- Calculate confidence based on:
  - Serial number clarity (found vs ambiguous)
  - Device issue clarity (explicit problem vs vague)
  - Email completeness (sufficient info vs missing context)
- Keywords indicating device issues: broken, faulty, not working, malfunction, RMA, defective, failed, error, problem
- **Be aggressive with valid-warranty**: Serial + any device issue keyword = valid-warranty
</analysis-guidelines>

<output-format>
Return valid JSON in this exact format:
{
  "scenario": "scenario-name",
  "serial_number": "extracted-serial-or-null",
  "confidence": 0.95
}

Where:
- scenario: One of [valid-warranty, invalid-warranty, missing-info, out-of-scope]
- serial_number: Extracted serial number string or null if not found
- confidence: Float 0.0-1.0 indicating detection confidence
</output-format>

<examples>
Example 1 - RMA with serial (VALID WARRANTY):
Email: "The gateway C074AD3D3101 is not working correctly. It's in some 'emergency mode' and we can't recover it."
Output: {"scenario": "valid-warranty", "serial_number": "C074AD3D3101", "confidence": 0.95}

Example 2 - RMA without serial (MISSING INFO):
Email: "Our Mediant device stopped working yesterday. Can you help?"
Output: {"scenario": "missing-info", "serial_number": null, "confidence": 0.90}

Example 3 - Device issue with serial (VALID WARRANTY):
Email: "Reporting RMA for broken device SN-12345. Device won't boot."
Output: {"scenario": "valid-warranty", "serial_number": "SN-12345", "confidence": 0.98}

Example 4 - Not warranty related (GRACEFUL DEGRADATION):
Email: "How much does the M500L cost? Where can I purchase it?"
Output: {"scenario": "graceful-degradation", "serial_number": null, "confidence": 0.95}

Example 5 - Warranty question with serial (VALID WARRANTY):
Email: "Can you check warranty for serial ABC123? Device has errors."
Output: {"scenario": "valid-warranty", "serial_number": "ABC123", "confidence": 0.97}
</examples>
