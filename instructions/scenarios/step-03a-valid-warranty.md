---
name: step-03a-valid-warranty
description: Step 3a - Create support ticket for valid warranty
trigger: step-03a-valid-warranty
version: 1.0.0
available_functions:
  - name: create_ticket
    description: Create a support ticket for warranty service request. Use after confirming valid warranty.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number
        customer_email:
          type: string
          description: Customer email address
        warranty_status:
          type: string
          description: Warranty status (valid, expired, not_found)
        priority:
          type: string
          description: Ticket priority level
          enum: [low, normal, high, urgent]
        category:
          type: string
          description: Ticket category
      required: [serial_number, customer_email, warranty_status, priority, category]
---

<objective>
Step 3a: Create Support Ticket

The warranty check returned VALID status. Create a support ticket for this warranty claim.

WORKFLOW:
1. Call create_ticket() with the warranty details
2. Save the ticket_id from the response
3. Return control indicating next step is 05-send-confirmation with the ticket_id

This is a SINGLE ACTION step - only create the ticket. Do NOT send email yet.
</objective>

<instructions>
Call create_ticket with these parameters:
- serial_number: Use the serial number from previous steps
- customer_email: Customer's email address
- warranty_status: "valid"
- priority: "normal"
- category: "warranty_claim"

Wait for the response which will include:
- ticket_id: Save this for the next step
- status: "created"
- created_at: Timestamp

Example response:
```json
{
  "ticket_id": "TKT-12345",
  "status": "created",
  "created_at": "2025-01-15T10:30:00Z"
}
```
</instructions>

<next-step>
After create_ticket succeeds:
→ Proceed to step-05-send-confirmation with parameters:
  - ticket_id (from create_ticket response)
  - serial_number
  - customer_email
  - warranty_expiration_date
</next-step>

<language>
**CRITICAL: This is a function calling step - no Polish text needed yet.**
The Polish email will be sent in step 05-send-confirmation.
</language>
