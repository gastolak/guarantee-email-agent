# Warranty Email Agent - Step-by-Step Workflow

This agent uses a simple state machine where each step is a separate instruction file.

## Workflow Diagram

```
START: Customer Email
        ↓
    [01-extract-serial]
    "Does customer have serial?"
        ↓
    ┌───┴───┬───────────────┐
    ↓       ↓               ↓
 Serial   No Serial    Out of Scope
  Found   Found
    ↓       ↓               ↓
[02-check-  [03d-request-  [04-out-of-
 warranty]   serial]        scope]
"Call API"    ↓              ↓
    ↓       DONE           DONE
 Get API
Response
    ↓
┌───┴───┬────────┬──────────┐
↓       ↓        ↓          ↓
Valid   Expired  Not Found  Error
↓       ↓        ↓          ↓
[03a-   [03c-   [03b-     [04-out-of-
valid-  expired- device-   scope]
warranty] warranty] not-found]  ↓
↓       ↓        ↓         DONE
Create  Send     Ask for
Ticket  Paid     Correct
↓      Repair   Serial
↓       ↓        ↓
[05-send- DONE    DONE
confirmation]
↓
Send Email
with ticket_id
↓
DONE
```

## Step Files

| Step | File | Purpose | Next Steps |
|------|------|---------|------------|
| 1 | `01-extract-serial.md` | Determine if customer provided serial number | `02-check-warranty` OR `03d-request-serial` OR `04-out-of-scope` |
| 2 | `02-check-warranty.md` | Call `check_warranty()` API function | Based on API response: `03a`, `03b`, `03c`, or `04` |
| 3a | `03a-valid-warranty.md` | Create support ticket (returns ticket_id) | `05-send-confirmation` |
| 3b | `03b-device-not-found.md` | Serial not in system - ask to verify | DONE |
| 3c | `03c-expired-warranty.md` | Warranty expired - offer paid repair | DONE |
| 3d | `03d-request-serial.md` | No serial provided - request it | DONE |
| 4 | `04-out-of-scope.md` | Not a warranty issue - redirect | DONE |
| 5 | `05-send-confirmation.md` | Send confirmation email with ticket_id | DONE |

## How It Works

1. **Agent starts at Step 1** (`01-extract-serial.md`)
2. **LLM decides next step** based on the current step's instructions
3. **Agent loads that step's instruction file** and executes it
4. **Process repeats** until reaching DONE

## Key Principles

- **One step at a time**: Each step has ONE job
- **Clear transitions**: Each step explicitly states which steps can come next
- **API calls happen at specific steps**: Only `02-check-warranty.md` calls the warranty API
- **No assumptions**: Agent must follow the steps in order, can't skip steps
