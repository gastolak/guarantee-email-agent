# Story 4.5: LLM Function Calling Architecture with Gemini

**Epic:** Epic 4 - Evaluation Framework
**Status:** Ready
**Priority:** High
**Estimated Effort:** 5-8 points (Medium)
**Created:** 2026-01-18
**Updated:** 2026-01-19
**Dependencies:** Story 4.1 (Eval Framework), Story 3.6 (Email Processing Pipeline)

## Problem Statement

The current architecture hardcodes which clients to call in the Python code (processor.py). This creates several limitations:

1. **Inflexible scenario handling**: All warranty inquiries call the same warranty API regardless of scenario needs
2. **No per-scenario tool selection**: Can't specify different tools for different scenarios
3. **Missed LLM capabilities**: Not leveraging LLM's reasoning to decide when/which tools to use
4. **Scalability issues**: Adding new scenarios or tools requires Python code changes

**Example of current limitation:**
- `missing-info` scenario shouldn't call warranty API (no serial number), but architecture requires it
- `valid-warranty` scenario needs both warranty check + ticket creation
- `invalid-warranty` scenario needs only warranty check (no ticket)
- Future scenarios (e.g., `product-inquiry`) might need different tools (knowledge base, CRM)

## Desired Outcome

Implement LLM function calling architecture where:

1. **LLM decides which functions to call** based on scenario instructions and email content
2. **Scenario instructions declare available functions** in YAML frontmatter
3. **Function execution is handled by a simple dispatcher** (mocked for eval, real for production)
4. **Eval framework tests function-calling behavior** with deterministic mock responses
5. **Agent uses same architecture** for both eval (mocks) and production (real clients)

**Success Criteria:**
- Gemini's function calling API integrated with scenario-specific function definitions
- LLM autonomously decides when to call `check_warranty`, `create_ticket`, etc.
- Scenario instructions specify available functions without Python code changes
- Eval tests validate correct function usage per scenario
- Mock clients return deterministic data for eval
- All existing eval tests pass with new architecture
- Pass rate ≥99% maintained (NFR1)

## User Story

**As a** warranty email agent developer
**I want** the LLM to decide which functions to call based on scenario instructions
**So that** I can add new scenarios and tools without changing Python code, and leverage LLM reasoning for intelligent function selection

## Acceptance Criteria

### AC1: Scenario Instructions Declare Available Functions
- [ ] Scenario instruction YAML frontmatter includes `available_functions` list
- [ ] Function definitions include: function name, description, parameter schema
- [ ] Example: `valid-warranty.md` declares `check_warranty` and `create_ticket`
- [ ] Example: `missing-info.md` declares no functions (empty list)
- [ ] Function schemas follow Gemini's function declaration format

**Example YAML frontmatter:**
```yaml
---
name: valid-warranty
description: Response for valid warranty inquiries
available_functions:
  - name: check_warranty
    description: Check warranty status for a product serial number. Returns warranty status, expiration date, and coverage details.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number to check
      required: [serial_number]

  - name: create_ticket
    description: Create support ticket for valid warranty RMA. Only call after confirming warranty is valid.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number
        customer_email:
          type: string
          description: Customer email address
        priority:
          type: string
          enum: [low, normal, high, urgent]
          description: Ticket priority level
      required: [serial_number, customer_email, priority]

  - name: send_email
    description: Send email response to the customer. Call this as the LAST step after gathering all information.
    parameters:
      type: object
      properties:
        to:
          type: string
          description: Recipient email address
        subject:
          type: string
          description: Email subject line
        body:
          type: string
          description: Email body content (in Polish)
      required: [to, subject, body]
---
```

### AC2: Gemini Provider Supports Function Calling
- [ ] `GeminiProvider` implements `create_message_with_functions()` method
- [ ] Uses `google.generativeai` function calling API
- [ ] Handles function call requests from LLM
- [ ] Executes function calls via dispatcher
- [ ] Returns function results to LLM for final response generation
- [ ] Supports multi-turn function calling (LLM → function → LLM → function → response)
- [ ] Temperature defaults to 0 per NFR1 (maximum determinism), configurable for testing

**API signature:**
```python
async def create_message_with_functions(
    self,
    system_prompt: str,
    user_prompt: str,
    available_functions: List[FunctionDefinition],
    function_dispatcher: FunctionDispatcher,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> FunctionCallingResult:
    """Generate response with function calling support.

    Args:
        system_prompt: System instruction for the LLM
        user_prompt: User message/query
        available_functions: List of functions the LLM can call
        function_dispatcher: Dispatcher to execute function calls
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature

    Returns:
        FunctionCallingResult with:
        - response_text: Final LLM response
        - function_calls: List of functions called (name, args, results)
        - total_turns: Number of conversation turns
    """
```

### AC3: Function Dispatcher Routes Calls to Clients
- [ ] `FunctionDispatcher` class routes function calls to correct client methods
- [ ] Maps function names to client methods:
  - `check_warranty` → `warranty_client.check_warranty()`
  - `create_ticket` → `ticketing_client.create_ticket()`
  - `send_email` → `gmail_client.send_email()`
- [ ] Validates function parameters against schema
- [ ] Returns structured function results
- [ ] Handles execution errors gracefully
- [ ] Logs all function calls with input/output for debugging
- [ ] Supports both mock clients (eval) and real clients (production)

**Implementation:**
```python
class FunctionDispatcher:
    """Dispatch function calls to appropriate clients."""

    def __init__(
        self,
        warranty_client: WarrantyClient,
        ticketing_client: TicketingClient,
        gmail_client: GmailClient
    ):
        self._handlers: Dict[str, Callable] = {
            "check_warranty": warranty_client.check_warranty,
            "create_ticket": ticketing_client.create_ticket,
            "send_email": gmail_client.send_email,
        }

    async def execute(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute function call and return result.

        Args:
            function_name: Name of function to call
            arguments: Function arguments

        Returns:
            Function execution result

        Raises:
            ValueError: If function_name is unknown
        """
        if function_name not in self._handlers:
            raise ValueError(f"Unknown function: {function_name}")

        handler = self._handlers[function_name]
        result = await handler(**arguments)

        logger.info(
            "Function executed",
            extra={
                "function": function_name,
                "arguments": arguments,
                "result_keys": list(result.keys()) if isinstance(result, dict) else None
            }
        )

        return result
```

### AC4: Email Processor Uses Function-Calling Architecture
- [ ] `EmailProcessor.process_email()` refactored to use function-calling
- [ ] Loads scenario instruction with function definitions
- [ ] Passes available functions to LLM provider
- [ ] Executes function calls via dispatcher
- [ ] Handles multi-turn function calling loop
- [ ] Maintains same processing steps (parse → extract → detect → generate)
- [ ] Backwards compatible with scenarios that don't use functions

**Processing flow:**
```python
# Step 1-3: Parse, Extract, Detect (unchanged)
email = self.parser.parse_email(raw_email)
serial_result = await self.extractor.extract_serial_number(email)
detection_result = await self.detector.detect_scenario(email, serial_result)

# Step 4: Load scenario with function definitions
scenario_instruction = self.router.select_scenario(detection_result.scenario_name)
available_functions = scenario_instruction.get_available_functions()

# Step 5: Execute with function calling - LLM controls entire workflow
# LLM will call check_warranty, create_ticket, and send_email as needed
result = await self.response_generator.generate_with_functions(
    scenario_instruction=scenario_instruction,
    email=email,  # Full email object for context
    serial_number=serial_result.serial_number,
    available_functions=available_functions,
    function_dispatcher=self.function_dispatcher
)

# Step 6: Validate email was sent (required for all scenarios)
if not result.email_sent:
    raise ProcessingError(
        message="LLM did not send email response",
        code="email_not_sent",
        details={"scenario": detection_result.scenario_name}
    )
```

### AC5: Eval Framework Tests Function-Calling Behavior
- [ ] Eval test cases specify expected function calls via `expected_function_calls`
- [ ] `EvalExpectedOutput` model includes `expected_function_calls` field
- [ ] `EvalResult` model includes `actual_function_calls` for comparison
- [ ] Validation checks: correct functions called, correct parameters, correct order
- [ ] Mock dispatcher returns deterministic responses from `mock_function_responses`
- [ ] Function call history tracked and displayed in eval results
- [ ] Validation failures include detailed diff (expected vs actual)

**Eval Data Models (updated):**
```python
# src/guarantee_email_agent/eval/models.py

@dataclass(frozen=True)
class ExpectedFunctionCall:
    """Expected function call in eval test case."""
    function_name: str
    arguments: Optional[Dict[str, Any]] = None      # Exact match
    arguments_contain: Optional[Dict[str, Any]] = None  # Partial match
    result_contains: Optional[Dict[str, Any]] = None    # Validate result
    body_contains: Optional[List[str]] = None       # For send_email body

@dataclass(frozen=True)
class ActualFunctionCall:
    """Actual function call recorded during eval execution."""
    function_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    execution_time_ms: int
    error_message: Optional[str] = None

@dataclass
class EvalResult:
    """Result of executing one eval test case."""
    test_case: EvalTestCase
    passed: bool
    failures: List[str]
    actual_output: Dict[str, Any]
    processing_time_ms: int
    actual_function_calls: List[ActualFunctionCall]  # NEW: Track all calls
```

**Function Call Validation Logic:**
```python
# src/guarantee_email_agent/eval/validator.py

def validate_function_calls(
    expected: List[ExpectedFunctionCall],
    actual: List[ActualFunctionCall]
) -> List[str]:
    """Validate function calls match expectations.

    Returns list of failure messages (empty if all pass).
    """
    failures = []

    # Check count matches
    if len(actual) != len(expected):
        failures.append(
            f"Function call count mismatch: expected {len(expected)}, got {len(actual)}"
        )
        # List what was called
        actual_names = [fc.function_name for fc in actual]
        expected_names = [fc.function_name for fc in expected]
        failures.append(f"  Expected: {expected_names}")
        failures.append(f"  Actual: {actual_names}")
        return failures

    # Check each call in order
    for i, (exp, act) in enumerate(zip(expected, actual)):
        # Check function name
        if exp.function_name != act.function_name:
            failures.append(
                f"Call {i+1}: Expected {exp.function_name}, got {act.function_name}"
            )
            continue

        # Check arguments (exact match)
        if exp.arguments:
            for key, value in exp.arguments.items():
                if key not in act.arguments:
                    failures.append(f"Call {i+1} {exp.function_name}: Missing argument '{key}'")
                elif act.arguments[key] != value:
                    failures.append(
                        f"Call {i+1} {exp.function_name}: Argument '{key}' "
                        f"expected '{value}', got '{act.arguments[key]}'"
                    )

        # Check arguments (partial match)
        if exp.arguments_contain:
            for key, value in exp.arguments_contain.items():
                if key not in act.arguments:
                    failures.append(f"Call {i+1} {exp.function_name}: Missing argument '{key}'")
                elif act.arguments[key] != value:
                    failures.append(
                        f"Call {i+1} {exp.function_name}: Argument '{key}' "
                        f"expected '{value}', got '{act.arguments[key]}'"
                    )

        # Check result contains expected values
        if exp.result_contains:
            for key, value in exp.result_contains.items():
                if key not in act.result:
                    failures.append(f"Call {i+1} {exp.function_name}: Result missing '{key}'")
                elif act.result[key] != value:
                    failures.append(
                        f"Call {i+1} {exp.function_name}: Result '{key}' "
                        f"expected '{value}', got '{act.result[key]}'"
                    )

        # Check send_email body content
        if exp.body_contains and exp.function_name == "send_email":
            body = act.arguments.get("body", "")
            for phrase in exp.body_contains:
                if phrase.lower() not in body.lower():
                    failures.append(
                        f"Call {i+1} send_email: Body missing phrase '{phrase}'"
                    )

    return failures
```

**Eval Reporter Output (with function calls):**
```
Running evaluation suite... (3 scenarios)

✓ valid_warranty_001: Customer with valid warranty requests status check
  Function calls:
    1. ✓ check_warranty(serial_number="SN12345")
       → {"status": "valid", "expiration_date": "2025-12-31"}
    2. ✓ create_ticket(serial_number="SN12345", customer_email="...")
       → {"ticket_id": "TKT-12345"}
    3. ✓ send_email(to="customer@example.com", subject="...", body="...")
       → {"message_id": "msg-123", "status": "sent"}

✗ invalid_warranty_001: Customer with expired warranty - FAILED
  Function calls:
    1. ✓ check_warranty(serial_number="SN98765")
       → {"status": "expired", "expiration_date": "2024-06-15"}
    2. ✗ send_email - Body missing phrase 'SN98765'
  Failures:
    - Call 2 send_email: Body missing phrase 'SN98765'

✓ missing_info_001: Customer inquiry without serial number
  Function calls:
    1. ✓ send_email(to="customer@example.com", subject="...", body="...")
       → {"message_id": "msg-456", "status": "sent"}

Pass rate: 2/3 (66.7%)
```

**Eval test case format:**
```yaml
scenario_id: valid_warranty_002
description: Valid warranty with function calling

input:
  email:
    subject: "RMA request"
    body: "I need RMA for serial number SN12345"
    from: "customer@example.com"
    received: "2026-01-18T10:00:00Z"

  # Mock function responses - dispatcher returns these
  mock_function_responses:
    check_warranty:
      serial_number: "SN12345"
      status: "valid"
      expiration_date: "2025-12-31"
    create_ticket:
      ticket_id: "TKT-12345"
      status: "created"
    send_email:
      message_id: "msg-abc123"
      status: "sent"

expected_output:
  scenario_instruction_used: "valid-warranty"

  # Expected function calls (in order) - PRIMARY VALIDATION
  expected_function_calls:
    - function_name: check_warranty
      arguments:
        serial_number: "SN12345"
      result_contains:
        status: "valid"

    - function_name: create_ticket
      arguments_contain:
        serial_number: "SN12345"
        customer_email: "customer@example.com"

    - function_name: send_email
      arguments_contain:
        to: "customer@example.com"
      body_contains:
        - "gwarancja"  # Polish for "warranty"
        - "2025-12-31"
        - "TKT-12345"
```

### AC6: All Scenarios Have send_email Function
- [ ] `valid-warranty.md`: `check_warranty` + `create_ticket` + `send_email`
- [ ] `invalid-warranty.md`: `check_warranty` + `send_email`
- [ ] `missing-info.md`: `send_email` only (no data lookup needed)
- [ ] `graceful-degradation.md`: `send_email` only
- [ ] All scenarios MUST call `send_email` as final step
- [ ] All scenario instructions include function usage guidance in `<objective>`
- [ ] LLM composes email content based on gathered information

### AC7: Validation and Error Handling
- [ ] Processing fails if LLM does not call `send_email` (required for all scenarios)
- [ ] Function call errors are logged and reported to LLM for recovery
- [ ] Max 10 function call iterations to prevent infinite loops
- [ ] Performance benchmarks show <15s total function-calling overhead
- [ ] All NFRs still met (NFR7: <60s processing, NFR1: ≥99% pass rate)

## Technical Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Scenario Instruction (valid-warranty.md)                       │
│  - available_functions: [check_warranty, create_ticket, send_email]
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  ResponseGenerator.generate_with_functions()                    │
│  - Builds system prompt with scenario instruction               │
│  - Builds user prompt with email content + serial number        │
│  - Converts functions to Gemini Tool format                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  GeminiProvider.create_message_with_functions()                 │
│  - LLM decides: "First, check warranty for SN12345"             │
│  - Returns function_call: check_warranty                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  FunctionDispatcher.execute("check_warranty", {serial: "SN12345"})
│  - Returns: {status: "valid", expiration_date: "2025-12-31"}    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  GeminiProvider (turn 2)                                        │
│  - LLM sees warranty is valid                                   │
│  - LLM decides: "Create ticket for valid warranty"              │
│  - Returns function_call: create_ticket                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  FunctionDispatcher.execute("create_ticket", {...})             │
│  - Returns: {ticket_id: "TKT-123", status: "created"}           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  GeminiProvider (turn 3)                                        │
│  - LLM has all info: warranty valid, ticket created             │
│  - LLM decides: "Send email response to customer"               │
│  - Returns function_call: send_email                            │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  FunctionDispatcher.execute("send_email", {                     │
│    to: "customer@example.com",                                  │
│    subject: "Re: RMA request",                                  │
│    body: "Szanowny Kliencie, Twoja gwarancja jest ważna..."     │
│  })                                                             │
│  - Returns: {message_id: "msg-123", status: "sent"}             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  GeminiProvider (complete)                                      │
│  - LLM confirms: "Email sent successfully"                      │
│  - Returns FunctionCallingResult with email_sent=true           │
└─────────────────────────────────────────────────────────────────┘
```

### File Changes

**New Files:**
1. `src/guarantee_email_agent/llm/function_calling.py` - Function calling models and utilities
2. `src/guarantee_email_agent/llm/function_dispatcher.py` - Function dispatcher
3. `src/guarantee_email_agent/instructions/function_loader.py` - Load function definitions from YAML
4. `src/guarantee_email_agent/eval/validator.py` - Function call validation logic
5. `tests/llm/test_function_calling.py` - Unit tests for function-calling
6. `tests/llm/test_function_dispatcher.py` - Dispatcher tests
7. `tests/eval/test_function_validation.py` - Eval function validation tests

**Modified Files:**
1. `src/guarantee_email_agent/llm/provider.py`
   - Add `create_message_with_functions()` to `GeminiProvider`
   - Add function-calling loop logic

2. `src/guarantee_email_agent/llm/response_generator.py`
   - Add `generate_with_functions()` method
   - Support both standard and function-calling generation

3. `src/guarantee_email_agent/email/processor.py`
   - Refactor to use function-calling architecture
   - Add function call tracking for logging

4. `src/guarantee_email_agent/instructions/loader.py`
   - Parse `available_functions` from YAML frontmatter
   - Validate function schemas

5. `src/guarantee_email_agent/eval/models.py`
   - Add `expected_function_calls` to `EvalExpectedOutput`
   - Add `function_calls` to `EvalResult`

6. `src/guarantee_email_agent/eval/runner.py`
   - Track function calls during eval execution
   - Validate function usage against expectations

7. `instructions/scenarios/valid-warranty.md`
   - Add `available_functions` to frontmatter
   - Update objective with function usage guidance

8. `instructions/scenarios/invalid-warranty.md`
   - Add `check_warranty` function only

9. `instructions/scenarios/missing-info.md`
   - Set `available_functions: []` (no functions needed)

### Data Models

```python
# src/guarantee_email_agent/llm/function_calling.py

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class FunctionParameter(BaseModel):
    """Parameter definition for a function."""
    type: str
    description: str
    enum: Optional[List[str]] = None


class FunctionDefinition(BaseModel):
    """Function definition for LLM function-calling."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for function parameters

    def to_gemini_tool(self) -> Dict[str, Any]:
        """Convert to Gemini Tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class FunctionCall(BaseModel):
    """Record of a function call execution."""
    function_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    execution_time_ms: int
    success: bool
    error_message: Optional[str] = None


class FunctionCallingResult(BaseModel):
    """Result from LLM generation with function calling."""
    response_text: str
    function_calls: List[FunctionCall]
    total_turns: int
    email_sent: bool = False  # True if send_email was called successfully
```

### Gemini Function-Calling Implementation

```python
# In src/guarantee_email_agent/llm/provider.py

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider with function calling support."""

    async def create_message_with_functions(
        self,
        system_prompt: str,
        user_prompt: str,
        available_functions: List[FunctionDefinition],
        function_dispatcher: FunctionDispatcher,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> FunctionCallingResult:
        """Generate response with function calling support."""

        # Convert functions to Gemini Tool format
        function_declarations = [
            FunctionDeclaration(
                name=f.name,
                description=f.description,
                parameters=f.parameters
            )
            for f in available_functions
        ]
        tools = [Tool(function_declarations=function_declarations)]

        # Create model with tools
        model = genai.GenerativeModel(
            self.config.model,
            tools=tools,
            system_instruction=system_prompt
        )

        # Start chat for multi-turn conversation
        chat = model.start_chat()
        function_calls: List[FunctionCall] = []
        total_turns = 0

        # Initial message
        response = chat.send_message(user_prompt)
        total_turns += 1

        # Function calling loop (max 10 iterations)
        while total_turns < 10:
            # Check if LLM wants to call a function
            if not response.candidates[0].content.parts:
                break

            part = response.candidates[0].content.parts[0]

            # Check for function call
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                function_name = fc.name
                arguments = dict(fc.args)

                # Execute function via dispatcher
                start_time = time.time()
                try:
                    result = await function_dispatcher.execute(
                        function_name=function_name,
                        arguments=arguments
                    )
                    execution_time_ms = int((time.time() - start_time) * 1000)

                    function_calls.append(FunctionCall(
                        function_name=function_name,
                        arguments=arguments,
                        result=result,
                        execution_time_ms=execution_time_ms,
                        success=True
                    ))

                    # Send function result back to LLM
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"result": result}
                                )
                            )]
                        )
                    )
                    total_turns += 1

                except Exception as e:
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    function_calls.append(FunctionCall(
                        function_name=function_name,
                        arguments=arguments,
                        result={},
                        execution_time_ms=execution_time_ms,
                        success=False,
                        error_message=str(e)
                    ))

                    # Send error back to LLM
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"error": str(e)}
                                )
                            )]
                        )
                    )
                    total_turns += 1

            else:
                # No function call - LLM has finished
                break

        # Extract final text response
        final_text = ""
        if response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if hasattr(part, 'text'):
                final_text = clean_markdown_response(part.text)

        # Check if email was sent via send_email function
        email_sent = any(fc.function_name == "send_email" and fc.success for fc in function_calls)

        return FunctionCallingResult(
            response_text=final_text,
            function_calls=function_calls,
            total_turns=total_turns,
            email_sent=email_sent
        )
```

### Scenario Instruction Updates

**instructions/scenarios/valid-warranty.md:**
```yaml
---
name: valid-warranty
description: Response instructions for valid warranty inquiries
trigger: valid-warranty
version: 2.0.0
available_functions:
  - name: check_warranty
    description: Check warranty status for a product serial number. Returns warranty status, expiration date, and coverage details. Always call this first.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number to check warranty for
      required: [serial_number]

  - name: create_ticket
    description: Create a support ticket for valid warranty RMA claims. Only call this AFTER check_warranty confirms the warranty is valid.
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number
        customer_email:
          type: string
          description: Customer email address
        priority:
          type: string
          enum: [low, normal, high, urgent]
          description: Ticket priority level
      required: [serial_number, customer_email, priority]

  - name: send_email
    description: Send email response to the customer. MUST be called as the final step.
    parameters:
      type: object
      properties:
        to:
          type: string
          description: Recipient email address
        subject:
          type: string
          description: Email subject line (in Polish)
        body:
          type: string
          description: Email body content (in Polish, professional tone)
      required: [to, subject, body]
---

<objective>
Handle valid warranty inquiries by checking warranty, creating ticket, and sending response.

**Function Usage (IMPORTANT - follow this order):**
1. Call check_warranty() with the serial number to verify status
2. If warranty is VALID: call create_ticket() to create RMA tracking
3. If warranty is NOT valid: skip create_ticket
4. ALWAYS call send_email() as the final step with a professional Polish response that includes:
   - Warranty status and expiration date
   - Ticket ID (if created)
   - Next steps for the customer
</objective>

[Rest of instruction unchanged...]
```

**instructions/scenarios/missing-info.md:**
```yaml
---
name: missing-info
description: Response for requests missing serial number
trigger: missing-info
version: 2.0.0
available_functions:
  - name: send_email
    description: Send email response to the customer asking for missing information.
    parameters:
      type: object
      properties:
        to:
          type: string
          description: Recipient email address
        subject:
          type: string
          description: Email subject line (in Polish)
        body:
          type: string
          description: Email body content (in Polish, helpful tone)
      required: [to, subject, body]
---

<objective>
Request the missing serial number from the customer.

**Function Usage:**
1. Call send_email() with a polite Polish response asking the customer to provide their product serial number
2. Include helpful guidance on where to find the serial number
</objective>

[Rest of instruction unchanged...]
```

## Implementation Plan

### Phase 1: Core Function-Calling Infrastructure (2-3 days)
**Tasks:**
1. Create `function_calling.py` with data models (FunctionDefinition, FunctionCall, FunctionCallingResult)
2. Create `FunctionDispatcher` class
3. Add `create_message_with_functions()` to `GeminiProvider`
4. Write unit tests for function-calling logic
5. Test with simple single-function scenario

**Deliverables:**
- Function-calling models defined
- Dispatcher routing function calls correctly
- Gemini provider executing function-calling loop
- Unit tests passing

### Phase 2: Scenario Function Definitions (1-2 days)
**Tasks:**
1. Update `InstructionLoader` to parse `available_functions` from YAML
2. Validate function schemas
3. Update scenario instructions with function definitions
4. Add function usage guidance to instruction objectives

**Deliverables:**
- Scenario instructions declare functions
- Function definitions validated against schemas
- All 4 scenarios updated (valid, invalid, missing, degradation)

### Phase 3: Email Processor Integration (2-3 days)
**Tasks:**
1. Refactor `EmailProcessor.process_email()` to use function-calling
2. Update `ResponseGenerator.generate_with_functions()`
3. Wire up dispatcher with existing clients
4. Add function call logging and tracking
5. Maintain backwards compatibility

**Deliverables:**
- Email processor uses function-calling architecture
- Function calls logged with input/output
- Existing functionality preserved
- Performance benchmarks meet targets

### Phase 4: Eval Framework Updates (1-2 days)
**Tasks:**
1. Add `expected_function_calls` to eval test case schema
2. Update `EvalRunner` to track and validate function calls
3. Update `EvalReporter` to show function call results
4. Create new eval test cases with function-calling expectations
5. Update existing eval tests as needed

**Deliverables:**
- Eval validates function usage
- Function call history in eval results
- All eval tests pass with function-calling
- Pass rate ≥99% maintained

## Testing Strategy

### Unit Tests
- `test_function_calling.py`: FunctionDefinition, FunctionCall, FunctionCallingResult models
- `test_function_dispatcher.py`: Dispatcher routing, error handling
- `test_gemini_function_calling.py`: Function-calling loop, multi-turn conversations
- `test_function_loader.py`: YAML parsing, schema validation

### Integration Tests
- `test_processor_with_functions.py`: End-to-end processing with function-calling
- `test_eval_function_validation.py`: Eval framework validates function usage
- `test_scenario_function_integration.py`: Each scenario uses correct functions

### Eval Tests
- Create 3+ new eval test cases per scenario with `expected_function_calls`
- Test cases cover:
  - Single function call (check_warranty only)
  - Multiple function calls (check_warranty + create_ticket)
  - No function calls (missing-info scenario)
  - Function call with error handling

## Non-Functional Requirements Impact

| NFR | Impact | Notes |
|-----|--------|-------|
| NFR1 (Pass Rate ≥99%) | Must maintain | Primary success metric |
| NFR7 (Processing <60s) | +5-10s per function call | Monitor closely |
| NFR11 (LLM Timeout 15s) | Per turn, not total | Each LLM call has 15s timeout |
| NFR5 (No Silent Failures) | Log all function calls | Full audit trail |
| NFR25 (Context for Debug) | Function history aids debugging | Improved observability |

## Risks and Mitigations

### Risk 1: LLM Makes Incorrect Function Calls
**Likelihood:** Medium | **Impact:** High
**Mitigation:**
- Clear function descriptions with usage guidance in scenario instructions
- Eval tests validate correct function usage patterns
- Add function call validation in dispatcher

### Risk 2: Performance Degradation
**Likelihood:** Low | **Impact:** Medium
**Mitigation:**
- Set max iterations limit (10) to prevent infinite loops
- Monitor function execution time
- Each function call adds ~2-5s (acceptable within 60s budget)

### Risk 3: Multi-Turn Debugging Complexity
**Likelihood:** Medium | **Impact:** Medium
**Mitigation:**
- Comprehensive logging of function calls and LLM responses
- Eval framework shows full function call history
- Add debug mode for verbose logging

### Risk 4: Breaking Existing Functionality
**Likelihood:** Low | **Impact:** High
**Mitigation:**
- Backwards compatible - scenarios without functions use standard generation
- All existing eval tests must pass
- Gradual migration per scenario

## Success Metrics

- [ ] All 4 scenarios support function-calling architecture
- [ ] ≥99% eval pass rate maintained (NFR1)
- [ ] P95 processing time <60s maintained (NFR7)
- [ ] Function-calling overhead <15s total
- [ ] Zero regressions in existing eval tests
- [ ] 100% of function calls logged with input/output

## Follow-Up Stories

**Story 4.6:** Anthropic Provider Function-Calling Support (optional, for multi-provider)
**Story 4.7:** Advanced Function-Calling (parallel execution, conditional functions)
**Story 5.1:** Production Client Implementation (real warranty API, ticketing)

## References

- [Gemini Function Calling Documentation](https://ai.google.dev/gemini-api/docs/function-calling)
- [Story 4.1: Eval Framework with Mocked Clients](./story-4.1-eval-framework-and-mocked-mcp-clients.md)
- [Story 3.6: Email Processing Pipeline Integration](./story-3.6-email-processing-pipeline-integration.md)

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-18 | Initial draft (Anthropic-focused) | - |
| 2026-01-19 | Rewritten for Gemini function calling | SM Agent |
