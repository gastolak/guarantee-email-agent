---
name: step-03b-device-not-found
description: Step 3b - Device not found in CRM system
version: 1.0.0
---

# Step 3b: Device Not Found - Request Correct Serial

The warranty check returned **DEVICE NOT FOUND**. The serial number is not in our system.

## Possible Reasons

1. Customer provided incorrect serial number
2. Serial number has a typo
3. Device not registered in our system
4. Serial from a different manufacturer

## Your Task

Send email asking customer to verify the serial number.

### Send Email
Call `send_email` function:
```
send_email(
  to="customer@example.com",
  subject="Re: Your warranty request - verify serial number",
  body="<Polish message asking to verify serial>"
)
```

## Email Template (Polish)

```
Dzień dobry,

Niestety nie odnaleźliśmy urządzenia o podanym numerze seryjnym "{serial_number}" w naszym systemie.

Prosimy o:
1. Sprawdzenie poprawności numeru seryjnego
2. Numer seryjny znajduje się na głównej tabliczce znamionowej urządzenia (zwykle na tyłu lub na spodzie urządzenia)
3. Przesłanie zdjęcia tabliczki znamionowej, jeśli numer jest nieczytelny

Po otrzymaniu prawidłowego numeru seryjnego ponownie sprawdzimy status gwarancji.

Pozdrawiamy,
Dział Serwisu
```

## Next Step

After sending email: **DONE** - wait for customer response with correct serial
