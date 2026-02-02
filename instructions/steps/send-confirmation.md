---
name: step-05-send-confirmation
description: Step 5 - Send confirmation email with ticket details
version: 1.0.0
available_functions:
  - name: send_email
    description: Send an email to the customer. Returns confirmation of delivery.
    parameters:
      type: object
      properties:
        to:
          type: string
          description: Recipient email address
        subject:
          type: string
          description: Email subject line
        body:
          type: string
          description: Email body content (can include Polish text)
      required: [to, subject, body]
---

# Step 5: Send Confirmation Email

Send email to customer confirming their warranty RMA request.

## Input Parameters (from previous steps)

You should have these values from previous steps:
- `ticket_id` - from Step 03a (create_ticket response)
- `serial_number` - from Step 01 (serial extraction)
- `customer_email` - from email headers
- `warranty_expiration_date` - from Step 02 (check_warranty response)

## Your Task

Send confirmation email to the customer.

### Send Email
Call `send_email` function:
```
send_email(
  to="<customer_email>",
  subject="Re: Your warranty request",
  body="<Polish confirmation message with ticket details>"
)
```

## Email Template (Polish)

Use the values from previous steps to fill in the template:

```
Dzień dobry,

Potwierdzamy przyjęcie zgłoszenia RMA dla urządzenia o numerze seryjnym {serial_number}.

Status gwarancji: AKTYWNA (ważna do {warranty_expiration_date})
Numer zgłoszenia: {ticket_id}

Nasz zespół techniczny skontaktuje się z Państwem w ciągu 2 dni roboczych w celu dalszych instrukcji.

Pozdrawiamy,
Dział Serwisu
```

## Next Step

After sending email: **DONE** - warranty RMA workflow complete

## Output Format

After sending the confirmation email, you **MUST** output:

```
NEXT_STEP: DONE
```
