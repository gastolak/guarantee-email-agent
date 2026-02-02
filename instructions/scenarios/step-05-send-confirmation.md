---
name: step-05-send-confirmation
description: Step 5 - Send confirmation email with ticket details
trigger: step-05-send-confirmation
version: 1.0.0
available_functions:
  - name: send_email
    description: Send email response to the customer. MUST be called to confirm warranty RMA request.
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
          description: Email body content in Polish
      required: [to, subject, body]
---

<objective>
Step 5: Send Confirmation Email

Send email to customer confirming their warranty RMA request with the ticket details.

INPUT PARAMETERS (from previous steps):
- ticket_id: Ticket number from step 03a (create_ticket response)
- serial_number: From step 01 (serial extraction)
- customer_email: Customer's email address
- warranty_expiration_date: From step 02 (check_warranty response)

WORKFLOW:
1. Build Polish confirmation email using the template below
2. Call send_email() with the formatted message
3. Mark workflow as DONE

This is the FINAL step - after sending email, the workflow is complete.
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<response-tone>
- Professional and reassuring (profesjonalny i uspokajający)
- Positive and helpful (pozytywny i pomocny)
- Clear and action-oriented (jasny i zorientowany na działanie)
- Warm but business-appropriate (ciepły ale odpowiedni dla biznesu)
</response-tone>

<email-template>
**Use this Polish template structure for confirmation emails:**

Dzień dobry,

Potwierdzamy przyjęcie zgłoszenia RMA dla urządzenia o numerze seryjnym {serial_number}.

Status gwarancji: AKTYWNA (ważna do {warranty_expiration_date})
Numer zgłoszenia: {ticket_id}

Nasz zespół techniczny skontaktuje się z Państwem w ciągu 2 dni roboczych w celu dalszych instrukcji.

Pozdrawiamy,
Dział Serwisu
</email-template>

<instructions>
Call send_email with:
- to: Customer's email address
- subject: "Re: Your warranty request"
- body: Polish formatted message using the template above with actual values

Make sure to:
1. Replace {serial_number} with the actual serial number
2. Replace {warranty_expiration_date} with the actual expiration date
3. Replace {ticket_id} with the ticket number from step 03a
4. Use proper Polish formatting and professional tone
</instructions>

<next-step>
After send_email succeeds:
→ DONE - Warranty RMA workflow complete
</next-step>

<avoid>
- Do not use overly casual language
- Do not make promises about specific repair timelines
- Do not apologize unnecessarily (warranty is valid - this is good news!)
- Do not include legal disclaimers unless specifically required
</avoid>
