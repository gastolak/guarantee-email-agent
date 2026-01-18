---
name: main-orchestration
description: Main orchestration instruction for warranty email processing
version: 1.0.0
---

<objective>
Process warranty inquiry emails by analyzing email content, extracting serial numbers, and determining the appropriate scenario for response generation.
</objective>

<workflow>
Follow this workflow for every email:
1. Analyze email content to understand customer intent
2. Extract serial number using the patterns defined below
3. Determine which scenario applies based on email characteristics
4. Return structured output with scenario, serial number, and confidence
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
- Customer is inquiring about warranty status
- Intent is to get warranty information

**invalid-warranty**:
- Email contains serial number
- Customer mentions warranty issue/expiration
- May be asking about expired warranty

**missing-info**:
- No serial number found in email body
- Serial number is ambiguous or unclear
- Multiple serial numbers without clear primary
- Customer request is unclear

**out-of-scope**:
- Email is not about warranty
- Spam, unrelated inquiry, or general support question
- No warranty-related keywords present

Default to **missing-info** if uncertain.
</scenario-detection>

<analysis-guidelines>
- Be conservative with scenario detection
- Prefer missing-info over valid-warranty if ambiguous
- Extract exact serial number text, preserve formatting
- Calculate confidence based on:
  - Serial number clarity (found vs ambiguous)
  - Intent clarity (warranty vs general question)
  - Email completeness (sufficient info vs missing context)
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
Example 1 - Valid warranty inquiry:
Email: "Hi, I need to check the warranty status for serial number SN12345. Thanks!"
Output: {"scenario": "valid-warranty", "serial_number": "SN12345", "confidence": 0.98}

Example 2 - Missing serial number:
Email: "I bought your product last year and need warranty info. Can you help?"
Output: {"scenario": "missing-info", "serial_number": null, "confidence": 0.92}

Example 3 - Out of scope:
Email: "How much does your product cost? Where can I buy it?"
Output: {"scenario": "out-of-scope", "serial_number": null, "confidence": 0.95}
</examples>
