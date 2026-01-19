# Story 4.5: LLM Function Calling Architecture with Gemini

Status: dev-complete

## Story

As a warranty email agent developer,
I want the LLM to decide which functions to call based on scenario instructions,
so that I can add new scenarios and tools without changing Python code, and leverage LLM reasoning for intelligent function selection.

## Acceptance Criteria

1. **Scenario instructions declare available functions** - YAML frontmatter includes `available_functions` list with name, description, and JSON Schema parameters for each function.

2. **GeminiProvider supports function calling** - Implements `create_message_with_functions()` using `google.generativeai` API with multi-turn conversation support and max 10 iterations.

3. **FunctionDispatcher routes calls to clients** - Maps function names (`check_warranty`, `create_ticket`, `send_email`) to existing client methods with logging and error handling.

4. **EmailProcessor uses function-calling architecture** - Refactored to load scenario functions, pass to LLM, execute via dispatcher, and validate `send_email` was called.

5. **Eval framework validates function calls** - Test cases specify `expected_function_calls` with argument matching, result validation, and `body_contains` for email content.

6. **All scenarios have send_email function** - `valid-warranty` (3 functions), `invalid-warranty` (2), `missing-info` (1), `graceful-degradation` (1). All MUST call `send_email` as final step.

7. **Validation and error handling** - Processing fails if `send_email` not called, function errors logged, max 10 iterations enforced, <15s overhead, NFR1 (≥99%) and NFR7 (<60s) maintained.

## Tasks / Subtasks

- [x] **Task 1: Create function calling data models** (AC: 1, 2)
  - [x] Create `src/guarantee_email_agent/llm/function_calling.py`
  - [x] Implement `FunctionDefinition` model with `to_gemini_tool()` method
  - [x] Implement `FunctionCall` model for tracking execution
  - [x] Implement `FunctionCallingResult` model with `email_sent` flag
  - [x] Write unit tests in `tests/llm/test_function_calling.py`

- [x] **Task 2: Create FunctionDispatcher** (AC: 3)
  - [x] Create `src/guarantee_email_agent/llm/function_dispatcher.py`
  - [x] Implement `execute(function_name, arguments)` method
  - [x] Map to existing clients: `warranty_client`, `ticketing_client`, `gmail_client`
  - [x] Add structured logging with `extra={"function": name, "arguments": args}`
  - [x] Handle unknown function with `ValueError`
  - [x] Write unit tests in `tests/llm/test_function_dispatcher.py`

- [x] **Task 3: Add function calling to GeminiProvider** (AC: 2)
  - [x] Add `create_message_with_functions()` method to `GeminiProvider`
  - [x] Use `genai.GenerativeModel` with `tools` parameter
  - [x] Implement multi-turn conversation loop via `model.start_chat()`
  - [x] Handle `function_call` in response parts
  - [x] Send `FunctionResponse` back to model after execution
  - [x] Track all function calls in `List[FunctionCall]`
  - [x] Enforce max 10 iterations
  - [x] Set `email_sent = True` if `send_email` succeeded
  - [x] Write integration tests

- [x] **Task 4: Update InstructionLoader for functions** (AC: 1)
  - [x] Modify `src/guarantee_email_agent/instructions/loader.py`
  - [x] Parse `available_functions` from YAML frontmatter
  - [x] Validate function schema (name, description, parameters required)
  - [x] Add `get_available_functions()` method to instruction model
  - [x] Write unit tests for function loading

- [x] **Task 5: Add generate_with_functions to ResponseGenerator** (AC: 4)
  - [x] Modify `src/guarantee_email_agent/llm/response_generator.py`
  - [x] Add `generate_with_functions()` method
  - [x] Build system prompt from scenario instruction
  - [x] Build user prompt with email content and serial number
  - [x] Call `provider.create_message_with_functions()`
  - [x] Return `FunctionCallingResult`

- [x] **Task 6: Refactor EmailProcessor for function calling** (AC: 4, 7)
  - [x] Modify `src/guarantee_email_agent/email/processor.py`
  - [x] Load scenario with `get_available_functions()`
  - [x] Create `FunctionDispatcher` with existing clients
  - [x] Call `generate_with_functions()` instead of `generate()`
  - [x] Validate `result.email_sent == True`
  - [x] Raise `ProcessingError` with code `email_not_sent` if false
  - [x] Log function call summary

- [x] **Task 7: Update scenario instructions** (AC: 1, 6)
  - [x] Update `instructions/scenarios/valid-warranty.md` - add 3 functions
  - [x] Update `instructions/scenarios/invalid-warranty.md` - add 2 functions
  - [x] Update `instructions/scenarios/missing-info.md` - add 1 function
  - [x] Update `instructions/scenarios/graceful-degradation.md` - add 1 function
  - [x] Add function usage guidance in `<objective>` section

- [x] **Task 8: Update eval models for function validation** (AC: 5)
  - [x] Modify `src/guarantee_email_agent/eval/models.py`
  - [x] Add `ExpectedFunctionCall` dataclass
  - [x] Add `ActualFunctionCall` dataclass
  - [x] Add `expected_function_calls` to `EvalExpectedOutput`
  - [x] Add `actual_function_calls` to `EvalResult`
  - [x] Add `mock_function_responses` to `EvalInput`

- [x] **Task 9: Create eval function validator** (AC: 5)
  - [x] Create `src/guarantee_email_agent/eval/validator.py`
  - [x] Implement `validate_function_calls(expected, actual)` function
  - [x] Check function count matches
  - [x] Check function names in order
  - [x] Check `arguments` (exact match) and `arguments_contain` (partial)
  - [x] Check `result_contains` for result validation
  - [x] Check `body_contains` for send_email body content
  - [x] Return list of failure messages
  - [x] Write unit tests in `tests/eval/test_function_validation.py`

- [x] **Task 10: Update EvalRunner for function tracking** (AC: 5)
  - [x] Modify `src/guarantee_email_agent/eval/runner.py`
  - [x] Create mock dispatcher from `mock_function_responses`
  - [x] Track actual function calls during execution
  - [x] Call `validate_function_calls()` after execution
  - [x] Add failures to result

- [x] **Task 11: Update EvalReporter for function display** (AC: 5)
  - [x] Modify `src/guarantee_email_agent/eval/reporter.py`
  - [x] Show function call trace for each scenario
  - [x] Format: `1. ✓ check_warranty(serial_number="...") → {result}`
  - [x] Show ✗ for failed validations with reason

- [x] **Task 12: Update eval test cases** (AC: 5)
  - [x] Update `evals/scenarios/valid_warranty_001.yaml` with function expectations
  - [x] Update other existing eval files
  - [x] Create additional eval cases covering function scenarios

- [ ] **Task 13: Run full eval suite and verify** (AC: 7)
  - [ ] Run `uv run python -m guarantee_email_agent eval` (requires GEMINI_API_KEY)
  - [ ] Verify pass rate ≥99%
  - [ ] Verify processing time <60s per scenario
  - [ ] Verify function call overhead <15s total

## Dev Notes

### Architecture Pattern

LLM controls entire workflow via function calling:
```
Email → Parse → Detect Scenario → Load Functions → LLM Loop → Done
                                         ↓
                              LLM: "call check_warranty"
                                         ↓
                              Dispatcher → warranty_client
                                         ↓
                              LLM: "call create_ticket"
                                         ↓
                              Dispatcher → ticketing_client
                                         ↓
                              LLM: "call send_email"
                                         ↓
                              Dispatcher → gmail_client
                                         ↓
                              Result: email_sent=true
```

### Gemini Function Calling API

Use `google.generativeai` types:
- `FunctionDeclaration(name, description, parameters)` - define function
- `Tool(function_declarations=[...])` - wrap functions
- `GenerativeModel(model, tools=[...], system_instruction=...)` - create model
- `model.start_chat()` - multi-turn conversation
- `chat.send_message(content)` - send user message or function response
- `response.candidates[0].content.parts[0].function_call` - check for function call
- `genai.protos.FunctionResponse(name, response={...})` - send result back

### Function Schema Format (Gemini)

```yaml
available_functions:
  - name: check_warranty
    description: Check warranty status for serial number
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number
      required: [serial_number]
```

### Eval Validation Flow

1. Load test case with `mock_function_responses`
2. Create mock dispatcher that returns mock responses
3. Run processor with mock dispatcher
4. Collect `actual_function_calls` from result
5. Compare against `expected_function_calls`:
   - Count matches
   - Names in order
   - Arguments match (exact or partial)
   - Results contain expected values
   - send_email body contains expected phrases

### Project Structure Notes

- All new files in `src/guarantee_email_agent/` following existing patterns
- Use `snake_case` for modules: `function_calling.py`, `function_dispatcher.py`
- Use `PascalCase` for classes: `FunctionDispatcher`, `FunctionCallingResult`
- Tests mirror src structure: `tests/llm/`, `tests/eval/`
- Eval scenarios in `evals/scenarios/` with `{category}_{number}.yaml` naming

### Critical Constraints

- **NFR1**: Must maintain ≥99% eval pass rate
- **NFR7**: Processing must complete in <60s (function overhead <15s)
- **NFR5**: Log ALL function calls with input/output
- **Temperature=0**: Use temperature=0 for deterministic function selection
- **Max iterations=10**: Prevent infinite function calling loops
- **send_email required**: All scenarios MUST call send_email as final step

### References

- [Source: _bmad-output/project-context.md#Technology Stack] - Gemini `gemini-2.0-flash-exp`, temperature=0
- [Source: _bmad-output/project-context.md#Async Patterns] - All MCP client methods are async
- [Source: _bmad-output/project-context.md#Structured Logging] - Use `extra={}` dict for logging
- [Source: _bmad-output/project-context.md#Error Handling] - Use `AgentError` hierarchy
- [Gemini Function Calling Docs](https://ai.google.dev/gemini-api/docs/function-calling)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**New Files:**
- `src/guarantee_email_agent/llm/function_calling.py`
- `src/guarantee_email_agent/llm/function_dispatcher.py`
- `src/guarantee_email_agent/eval/validator.py`
- `tests/llm/test_function_calling.py`
- `tests/llm/test_function_dispatcher.py`
- `tests/eval/test_function_validation.py`

**Modified Files:**
- `src/guarantee_email_agent/llm/provider.py`
- `src/guarantee_email_agent/llm/response_generator.py`
- `src/guarantee_email_agent/email/processor.py`
- `src/guarantee_email_agent/instructions/loader.py`
- `src/guarantee_email_agent/eval/models.py`
- `src/guarantee_email_agent/eval/runner.py`
- `src/guarantee_email_agent/eval/reporter.py`
- `instructions/scenarios/valid-warranty.md`
- `instructions/scenarios/invalid-warranty.md`
- `instructions/scenarios/missing-info.md`
- `instructions/scenarios/graceful-degradation.md`
- `evals/scenarios/valid_warranty_001.yaml`
