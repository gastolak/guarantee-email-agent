---
name: step-03d-request-serial
description: Step 3d - Request serial number from customer
version: 1.0.0
---

# Step 3d: Request Serial Number

Customer reported a device issue but did NOT provide a serial number.

## Your Task

Send email asking customer to provide the serial number.

### Send Email
Call `send_email` function:
```
send_email(
  to="customer@example.com",
  subject="Re: Your warranty request - serial number needed",
  body="<Polish message requesting serial>"
)
```

## Email Template (Polish)

```
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
```

## Next Step

After sending email: **DONE** - wait for customer to provide serial number
