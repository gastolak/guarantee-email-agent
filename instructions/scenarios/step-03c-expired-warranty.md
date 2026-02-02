---
name: step-03c-expired-warranty
description: Step 3c - Warranty expired - offer paid repair
trigger: step-03c-expired-warranty
version: 1.0.0
available_functions:
  - name: send_email
    description: Send email response to the customer about expired warranty.
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
Step 3c: Expired Warranty - Offer Paid Repair

The warranty check returned status="expired". The device warranty has ended.

WORKFLOW:
1. Send email informing customer about expired warranty
2. Offer paid repair option
3. Mark workflow as DONE - wait for customer decision
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<email-template>
**Use this Polish template:**

Dzień dobry,

Sprawdziliśmy status gwarancji dla urządzenia o numerze seryjnym {serial_number}.

Status gwarancji: WYGASŁA (data wygaśnięcia: {expiration_date})

Niestety gwarancja producenta już nie obowiązuje. Oferujemy jednak płatną naprawę urządzenia:

1. Darmowa diagnoza usterki
2. Wycena naprawy przed rozpoczęciem prac
3. 6 miesięcy gwarancji na wykonaną naprawę

Jeśli jest Państwo zainteresowani płatną naprawą, prosimy o potwierdzenie, a przygotujemy szczegóły procedury.

Pozdrawiamy,
Dział Serwisu
</email-template>

<instructions>
Call send_email with:
- to: Customer's email address
- subject: "Re: Your warranty request"
- body: Polish formatted message using the template above

Replace placeholders:
- {serial_number}: The device serial number
- {expiration_date}: The warranty expiration date from check_warranty response
</instructions>

<next-step>
After send_email succeeds:
→ DONE - Wait for customer decision on paid repair
</next-step>
