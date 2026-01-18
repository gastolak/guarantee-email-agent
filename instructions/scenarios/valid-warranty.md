---
name: valid-warranty
description: Response instructions for valid warranty inquiries
trigger: valid-warranty
version: 1.1.0
---

<objective>
Generate a professional, helpful response IN POLISH confirming the customer's warranty is valid and providing next steps for RMA service.
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

<required-information>
Include in response:
- Greeting and acknowledgment of their inquiry
- Confirmation that warranty is valid and active
- Warranty expiration date (from warranty API data)
- What the warranty covers (manufacturing defects, hardware failures under normal use)
- Clear next steps for claiming warranty service
- Contact information if they have questions
- Professional closing
</required-information>

<response-structure>
1. Greeting and acknowledgment
2. Warranty status confirmation (valid and active)
3. Warranty details (expiration date, coverage scope)
4. Next steps for initiating warranty service claim
5. Support contact information
6. Professional closing with signature
</response-structure>

<email-template>
**Use this Polish template structure for valid warranty responses:**

Dzień dobry [Imię],

Dziękujemy za kontakt w sprawie RMA dla urządzenia o numerze seryjnym {serial_number}.

Z przyjemnością potwierdzam, że gwarancja na to urządzenie jest **ważna i aktywna do dnia {warranty_expiration_date}**. Gwarancja obejmuje wady produkcyjne oraz usterki sprzętowe powstałe podczas normalnego użytkowania.

Aby kontynuować proces RMA, utworzymy zgłoszenie serwisowe. Nasz zespół techniczny skontaktuje się z Państwem w ciągu 24 godzin w celu ustalenia dalszych kroków naprawy lub wymiany urządzenia.

W razie pytań lub potrzeby pilnej pomocy, prosimy o kontakt:
- Email: support@example.com
- Telefon: +48 22 XXX XX XX

Pozdrawiam,
Zespół Wsparcia Gwarancyjnego
</email-template>

<examples>
Example Polish response for valid warranty with RMA:

"Dzień dobry Adam,

Dziękujemy za kontakt w sprawie RMA dla bramki Mediant o numerze seryjnym C074AD3D3101.

Z przyjemnością potwierdzam, że gwarancja na to urządzenie jest **ważna i aktywna do dnia 18 stycznia 2027**. Gwarancja obejmuje wady produkcyjne oraz usterki sprzętowe powstałe podczas normalnego użytkowania.

Aby kontynuować proces RMA, utworzymy zgłoszenie serwisowe. Nasz zespół techniczny skontaktuje się z Państwem w ciągu 24 godzin w celu ustalenia dalszych kroków naprawy lub wymiany urządzenia.

Rozumiemy również Państwa sugestię dotyczącą możliwości wymiany urządzenia M500Li na standardowy model M500 lub M500L. Nasz zespół inżynierski rozważy tę opcję podczas procesu RMA.

W razie pytań lub potrzeby pilnej pomocy, prosimy o kontakt:
- Email: support@example.com
- Telefon: +48 22 XXX XX XX

Pozdrawiam,
Zespół Wsparcia Gwarancyjnego"
</examples>

<avoid>
- Do not use overly casual language
- Do not make promises about specific repair timelines unless provided in warranty data
- Do not apologize unnecessarily (warranty is valid - this is good news!)
- Do not include legal disclaimers unless specifically required
</avoid>
