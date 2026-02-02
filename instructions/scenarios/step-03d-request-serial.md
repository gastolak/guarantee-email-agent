---
name: step-03d-request-serial
description: Step 3d - Request serial number from customer
trigger: step-03d-request-serial
version: 1.0.0
available_functions:
  - name: send_email
    description: Send email response requesting serial number from customer.
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
Step 3d: Request Serial Number

Customer reported a device issue but did NOT provide a serial number.

WORKFLOW:
1. Send email asking customer to provide the serial number
2. Mark workflow as DONE - wait for customer to provide serial
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<email-template>
**Use this Polish template:**

Dzień dobry,

Dziękujemy za kontakt w sprawie gwarancji urządzenia.

Aby sprawdzić status gwarancji, potrzebujemy numeru seryjnego urządzenia.

Numer seryjny można znaleźć:
- Na naklejce znamionowej urządzenia (zwykle na tyłu lub na spodzie)
- Format: SN12345 lub podobny kod alfanumeryczny
- W przypadku trudności z odczytaniem, prosimy o przesłanie zdjęcia tabliczki znamionowej

Po otrzymaniu numeru seryjnego niezwłocznie sprawdzimy status gwarancji.

Pozdrawiamy,
Dział Serwisu
</email-template>

<instructions>
Call send_email with:
- to: Customer's email address
- subject: "Re: Your warranty request - serial number needed"
- body: Polish formatted message using the template above
</instructions>

<next-step>
After send_email succeeds:
→ DONE - Wait for customer to provide serial number
</next-step>
