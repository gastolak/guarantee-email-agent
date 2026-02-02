---
name: step-03a-valid-warranty
description: Step 3a - Create support ticket for valid warranty
version: 1.0.0
available_functions:
  - name: create_ticket
    description: Create a support ticket for a warranty claim. Returns ticket ID and creation timestamp.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number for the warranty claim
        customer_email:
          type: string
          description: Customer email address
        issue_description:
          type: string
          description: Description of the device issue
        priority:
          type: string
          description: Ticket priority level
          enum: [low, normal, high, urgent]
      required: [serial_number, customer_email, issue_description, priority]
---

# Step 3a: Valid Warranty - Create Support Ticket

The warranty check returned **VALID** status. The device is covered under warranty.

## Your Task

Create a support ticket for this warranty claim.

### Create Support Ticket
Call `create_ticket` function:
```
create_ticket(
  serial_number="<serial from previous steps>",
  customer_email="<customer email address>",
  issue_description="Device broken/faulty - extracted from email",
  priority="normal"
)
```

**IMPORTANT**: Save the `ticket_id` from the response - you'll need it for the next step.

Example response:
```json
{
  "ticket_id": "TKT-12345",
  "status": "created",
  "created_at": "2025-01-15T10:30:00Z"
}
```

## Next Step

After creating ticket: **Go to Step 05 (send-confirmation)** with parameters:
- ticket_id (from create_ticket response)
- serial_number
- customer_email
- warranty_expiration_date

## Output Format

After creating the ticket, you **MUST** output:

```
NEXT_STEP: send-confirmation
```
