---
name: step-04-out-of-scope
description: Step 4 - Handle out-of-scope requests
version: 1.0.0
---

# Step 4: Out of Scope

The customer's email is NOT about a warranty RMA issue.

## Examples of Out of Scope

- Billing questions
- General product questions
- Sales inquiries
- Spam
- Unrelated topics

## Your Task

Send polite email redirecting customer to appropriate channel.

### Send Email
Call `send_email` function:
```
send_email(
  to="customer@example.com",
  subject="Re: Your inquiry",
  body="<Polish message redirecting>"
)
```

## Email Template (Polish)

```
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
```

## Next Step

After sending email: **DONE** - request handled
