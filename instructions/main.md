---
name: main-orchestration
description: Main entry point for warranty email processing workflow
version: 2.0.0
---

<objective>
Process warranty RMA emails for broken/faulty devices using a step-by-step workflow where each step is a separate instruction file.
</objective>

<workflow-overview>
This is a STATE MACHINE workflow. Each email enters at Step 01 and flows through subsequent steps based on the data and decisions at each step.

**Entry Point:**
→ Start at Step 01: Extract Serial Number

**Workflow Flow:**
```
START
  ↓
[01-extract-serial] ← YOU START HERE
  ↓
Based on serial extraction:
  - Serial found + warranty issue → [02-check-warranty]
  - No serial + warranty issue → [03d-request-serial] → DONE
  - Not warranty related → [04-out-of-scope] → DONE
  ↓
[02-check-warranty] calls check_warranty() API
  ↓
Based on API response:
  - status="valid" → [03a-valid-warranty] → [05-send-confirmation] → DONE
  - status="expired" → [03c-expired-warranty] → DONE
  - status="not_found" → [03b-device-not-found] → DONE
  - error → [04-out-of-scope] → DONE
```
</workflow-overview>

<step-routing>
Each step is defined in a separate scenario file in `instructions/scenarios/`:

- **step-01-extract-serial**: Handled by serial_extractor.py (automated)
- **step-02-check-warranty**: Call check_warranty() API, route based on response
- **step-03a-valid-warranty**: Create support ticket for valid warranty
- **step-03b-device-not-found**: Ask customer to verify serial number
- **step-03c-expired-warranty**: Offer paid repair for expired warranty
- **step-03d-request-serial**: Request serial number from customer
- **step-04-out-of-scope**: Redirect non-warranty requests
- **step-05-send-confirmation**: Send confirmation email with ticket details

Each scenario file contains:
- Function definitions (available_functions in YAML frontmatter)
- Step-specific instructions
- Polish email templates
- Next step routing logic
</step-routing>

<key-principles>
1. **ONE step = ONE action** - Each step does exactly one thing
2. **Explicit routing** - Each step states which steps can come next
3. **Parameter passing** - Data (ticket_id, serial_number, warranty_data) flows between steps
4. **No skipping** - Must follow the workflow order
5. **LLM decides** - Based on current step's output, LLM selects the next step
</key-principles>

<initial-classification>
The scenario detector classifies incoming emails to determine the entry point:

**valid-warranty** (most common):
- Email contains serial number + reports device issue
- Keywords: broken, faulty, not working, malfunction, RMA, defective, failed, error
- → Routes to Step 02 (check-warranty)

**missing-info**:
- No serial number + device issue mentioned
- → Routes to Step 03d (request-serial)

**out-of-scope**:
- Not about warranty (billing, sales, general support)
- → Routes to Step 04 (out-of-scope)
</initial-classification>
