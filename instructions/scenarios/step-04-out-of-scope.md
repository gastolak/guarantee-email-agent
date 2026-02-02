---
name: step-04-out-of-scope
description: Step 4 - Handle out-of-scope requests
trigger: step-04-out-of-scope
version: 1.0.0
available_functions:
  - name: send_email
    description: Send email response redirecting customer to appropriate channel.
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
Step 4: Out of Scope

The customer's email is NOT about a warranty RMA issue.

Examples of out-of-scope requests:
- Billing questions
- General product questions
- Sales inquiries
- Spam
- Unrelated topics
- API errors that prevent warranty processing

WORKFLOW:
1. Send polite email redirecting customer to appropriate channel
2. Mark workflow as DONE - request handled
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<email-template>
**Use this Polish template:**

Dzień dobry,

Dziękujemy za kontakt.

Niniejszy adres email obsługuje wyłącznie zgłoszenia serwisowe dotyczące gwarancji urządzeń.

W przypadku innych pytań prosimy o kontakt:
- Pytania ogólne: info@example.com
- Wsparcie techniczne: support@example.com
- Dział sprzedaży: sales@example.com

Przepraszamy za niedogodności.

Pozdrawiamy,
Dział Serwisu
</email-template>

<instructions>
Call send_email with:
- to: Customer's email address
- subject: "Re: Your inquiry"
- body: Polish formatted message using the template above
</instructions>

<next-step>
After send_email succeeds:
→ DONE - Request handled
</next-step>
