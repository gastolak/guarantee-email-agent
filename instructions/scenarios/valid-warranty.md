---
name: valid-warranty
description: Response instructions for valid warranty inquiries
trigger: valid-warranty
version: 1.0.0
---

<objective>
Generate a professional, helpful response confirming the customer's warranty is valid and providing next steps for service.
</objective>

<response-tone>
- Professional and reassuring
- Positive and helpful
- Clear and action-oriented
- Warm but business-appropriate
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

<examples>
Example of a good valid warranty response:

"Dear [Customer Name],

Thank you for contacting us regarding your warranty inquiry for serial number SN12345.

I'm pleased to confirm that your warranty is valid and active until December 31, 2025. Your warranty covers all manufacturing defects and hardware failures occurring under normal use conditions.

To proceed with a warranty claim, please follow these steps:
1. Visit our warranty portal at warranty.example.com
2. Submit a claim using your serial number SN12345
3. Our service team will contact you within 24 hours to arrange next steps

If you have any questions or need immediate assistance, please don't hesitate to reach out to our support team at support@example.com or call 1-800-WARRANTY.

Best regards,
Warranty Support Team"
</examples>

<avoid>
- Do not use overly casual language
- Do not make promises about specific repair timelines unless provided in warranty data
- Do not apologize unnecessarily (warranty is valid - this is good news!)
- Do not include legal disclaimers unless specifically required
</avoid>
