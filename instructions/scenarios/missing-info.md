---
name: missing-info
description: Response for requests missing serial number or required information
trigger: missing-info
version: 1.1.0
---

<objective>
Politely request IN POLISH the missing information needed to process the warranty inquiry, specifically the product serial number.
</objective>

<language>
**CRITICAL: All email responses MUST be written in Polish language.**
Use professional Polish business correspondence style.
</language>

<response-tone>
- Polite and patient (grzeczny i cierpliwy)
- Helpful and guiding (pomocny i prowadzący)
- Clear and specific (jasny i konkretny)
- Appreciative of their contact (doceniający kontakt)
</response-tone>

<required-information>
Include in response:
- Greeting and acknowledgment of inquiry
- Appreciation for contacting us
- Clear explanation of what information is needed (serial number)
- Detailed guidance on where to find the serial number
- Instructions on how to provide the information (reply to email)
- Assurance that we'll help once received
- Professional closing
</required-information>

<response-structure>
1. Greeting and acknowledgment
2. Thank customer for contacting us
3. Explain we need serial number to check warranty status
4. Provide specific guidance on finding serial number:
   - Product label/sticker location
   - Original packaging/box
   - Purchase receipt/invoice
   - Product manual/documentation
5. Request they reply with the serial number
6. Assure prompt assistance once received
7. Professional closing
</response-structure>

<email-template>
**Use this Polish template structure for missing-info responses:**

Dzień dobry [Imię],

Dziękujemy za kontakt w sprawie zgłoszenia RMA. Chętnie pomożemy!

Aby sprawdzić status gwarancji i przetworzyć Państwa zgłoszenie, potrzebujemy **numeru seryjnego urządzenia**. Ten unikalny identyfikator pozwoli nam na weryfikację szczegółów gwarancji.

**Numer seryjny można znaleźć w następujących miejscach:**
- Na naklejce lub etykiecie na samym urządzeniu (zwykle na spodzie, z tyłu lub wewnątrz komory baterii)
- Na oryginalnym opakowaniu produktu
- Na fakturze zakupu lub paragonie
- W dokumentacji produktu lub instrukcji obsługi

Numer seryjny zazwyczaj składa się z kombinacji liter i cyfr (np. C074AD3D3101, SN12345).

Proszę o odpowiedź na tę wiadomość z numerem seryjnym, a natychmiast sprawdzimy status gwarancji i pomożemy w dalszym procesie.

Jeśli będą Państwo mieli problem ze znalezieniem numeru seryjnego, proszę dać znać - chętnie pomożemy.

Pozdrawiam,
Zespół Wsparcia Gwarancyjnego
</email-template>

<examples>
Example Polish response for missing serial number:

"Dzień dobry,

Dziękujemy za kontakt w sprawie zgłoszenia RMA dla bramki Mediant. Chętnie pomożemy!

Aby sprawdzić status gwarancji i przetworzyć Państwa zgłoszenie, potrzebujemy **numeru seryjnego urządzenia**. Ten unikalny identyfikator pozwoli nam na weryfikację szczegółów gwarancji.

**Numer seryjny można znaleźć w następujących miejscach:**
- Na naklejce lub etykiecie na samym urządzeniu (zwykle na spodzie, z tyłu lub wewnątrz obudowy)
- Na oryginalnym opakowaniu produktu
- Na fakturze zakupu
- W dokumentacji produktu (Quick Start Guide)

Dla urządzeń Mediant, numer seryjny zazwyczaj składa się z 12 znaków alfanumerycznych (np. C074AD3D3101).

Proszę o odpowiedź na tę wiadomość z numerem seryjnym, a natychmiast sprawdzimy status gwarancji i pomożemy w dalszym procesie RMA.

Jeśli będą Państwo mieli problem ze znalezieniem numeru seryjnego, proszę dać znać - chętnie pomożemy.

Pozdrawiam,
Zespół Wsparcia Gwarancyjnego"
</examples>

<avoid>
- Do not be impatient or make customer feel they made a mistake
- Do not use technical jargon without explanation
- Do not provide too many options that might confuse
- Do not delay helping them find the information
</avoid>
