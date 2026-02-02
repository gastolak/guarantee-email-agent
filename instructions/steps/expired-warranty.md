---
name: step-03c-expired-warranty
description: Step 3c - Warranty expired - offer paid repair
version: 1.0.0
---

# Step 3c: Expired Warranty - Offer Paid Repair

The warranty check returned **EXPIRED** status. The device warranty has ended.

## Your Task

Send email informing customer about expired warranty and offering paid repair option.

### Send Email
Call `send_email` function:
```
send_email(
  to="customer@example.com",
  subject="Re: Your warranty request",
  body="<Polish message about expired warranty>"
)
```

## Email Template (Polish)

```
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
```

## Next Step

After sending email: **DONE** - wait for customer decision on paid repair
