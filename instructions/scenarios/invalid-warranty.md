---
name: invalid-warranty
description: Response instructions for expired or invalid warranty inquiries
trigger: invalid-warranty
version: 1.1.0
---

<objective>
Generate an empathetic, solution-oriented response IN POLISH explaining that the warranty has expired or is invalid, while offering alternative support options (paid repair).
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<response-tone>
- Empathetic and understanding (empatyczny i wyrozumiały)
- Solution-oriented (zorientowany na rozwiązania)
- Professional and respectful (profesjonalny i pełen szacunku)
- Helpful in providing alternatives (pomocny w oferowaniu alternatyw)
</response-tone>

<required-information>
Include in response:
- Greeting and acknowledgment of their inquiry
- Clear explanation that warranty has expired or is invalid
- Warranty expiration date (if applicable)
- Empathetic acknowledgment of their situation
- Alternative options (extended warranty, paid repair services, upgrade options)
- Contact information for paid support
- Professional closing
</required-information>

<response-structure>
1. Greeting and acknowledgment
2. Warranty status explanation (expired/invalid with date if available)
3. Empathetic acknowledgment
4. Alternative options and solutions
5. Next steps if they want to proceed with alternatives
6. Support contact information
7. Professional closing
</response-structure>

<email-template>
**Use this Polish template structure for invalid/expired warranty responses:**

Dzień dobry [Imię],

Dziękujemy za kontakt w sprawie RMA dla urządzenia o numerze seryjnym {serial_number}.

Po sprawdzeniu naszych systemów informuję, że gwarancja na to urządzenie **wygasła dnia {warranty_expiration_date}**. Rozumiem, że może to być rozczarowujące, dlatego chciałbym przedstawić Państwu dostępne opcje wsparcia.

**Oferujemy następujące alternatywy:**

1. **Płatna naprawa serwisowa** - Nasi certyfikowani technicy mogą zdiagnozować i naprawić urządzenie
2. **Możliwość wymiany na nowy model** - Rozważcie Państwo zakup nowszego urządzenia z nową gwarancją

Aby omówić szczegóły i uzyskać wycenę, prosimy o kontakt z naszym działem wsparcia:
- Email: support@example.com
- Telefon: +48 22 XXX XX XX

Cenimy Państwa jako klienta i chętnie pomożemy znaleźć najlepsze rozwiązanie.

Pozdrawiam,
Zespół Wsparcia Klienta
</email-template>

<examples>
Example Polish response for expired warranty:

"Dzień dobry,

Dziękujemy za kontakt w sprawie RMA dla bramki Mediant o numerze seryjnym C074AD3D3101.

Po sprawdzeniu naszych systemów informuję, że gwarancja na to urządzenie **wygasła dnia 15 czerwca 2024**. Rozumiem, że może to być rozczarowujące, dlatego chciałbym przedstawić Państwu dostępne opcje wsparcia.

**Oferujemy następujące alternatywy:**

1. **Płatna naprawa serwisowa** - Nasi certyfikowani technicy mogą zdiagnozować i naprawić urządzenie. Typowy czas naprawy: 5-7 dni roboczych.
2. **Możliwość wymiany na nowy model** - Rozważcie Państwo zakup nowszego urządzenia M500 lub M500L z 3-letnią gwarancją producenta.

Zrozumieliśmy również Państwa uwagę dotyczącą problemów z modelem M500Li. Ta informacja zostanie przekazana naszemu działowi technicznego.

Aby omówić szczegóły i uzyskać wycenę, prosimy o kontakt z naszym działem wsparcia:
- Email: support@example.com
- Telefon: +48 22 XXX XX XX

Cenimy Państwa jako klienta i chętnie pomożemy znaleźć najlepsze rozwiązanie.

Pozdrawiam,
Zespół Wsparcia Klienta"
</examples>

<avoid>
- Do not be abrupt or dismissive about expired warranty
- Do not apologize excessively (it's standard business practice)
- Do not make false promises about free service
- Do not suggest workarounds to warranty expiration
- Do not pressure customers into purchasing extended warranties
</avoid>
