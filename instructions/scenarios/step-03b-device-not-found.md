---
name: step-03b-device-not-found
description: Step 3b - Device not found in CRM system
trigger: step-03b-device-not-found
version: 1.0.0
available_functions:
  - name: send_email
    description: Send email response to the customer asking to verify serial number.
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
Step 3b: Device Not Found

The warranty check returned "Device not found". The serial number is not in our system.

Possible reasons:
1. Customer provided incorrect serial number
2. Serial number has a typo
3. Device not registered in our system
4. Serial from a different manufacturer

WORKFLOW:
1. Send email asking customer to verify the serial number
2. Mark workflow as DONE - wait for customer response
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<email-template>
**Use this Polish template:**

Dzień dobry,

Niestety nie odnaleźliśmy urządzenia o podanym numerze seryjnym "{serial_number}" w naszym systemie.

Prosimy o:
1. Sprawdzenie poprawności numeru seryjnego
2. Numer seryjny znajduje się na głównej tabliczce znamionowej urządzenia (zwykle na tyłu lub na spodzie urządzenia)
3. Przesłanie zdjęcia tabliczki znamionowej, jeśli numer jest nieczytelny

Po otrzymaniu prawidłowego numeru seryjnego ponownie sprawdzimy status gwarancji.

Pozdrawiamy,
Dział Serwisu
</email-template>

<instructions>
Call send_email with:
- to: Customer's email address
- subject: "Re: Your warranty request - verify serial number"
- body: Polish formatted message using the template above with the actual serial_number

Make sure to replace {serial_number} with the actual serial number that was not found.
</instructions>

<next-step>
After send_email succeeds:
→ DONE - Wait for customer response with correct serial
</next-step>
