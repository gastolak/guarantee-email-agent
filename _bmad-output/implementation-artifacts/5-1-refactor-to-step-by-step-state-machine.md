---
story_id: "5.1"
title: "Refactor to Step-by-Step State Machine Architecture"
category: "refactoring"
priority: "high"
epic: "Architecture Evolution"
estimated_effort: "5 days"
depends_on: ["4.6"]
status: "ready_for_dev"
created: "2026-02-02"
---

# Story 5.1: Refactor to Step-by-Step State Machine Architecture

## Context

**Current Architecture (Monolithic Scenarios):**
The agent currently uses a monolithic scenario approach where:
- `scenario_detector.py` classifies emails into 3 broad categories: `valid-warranty`, `missing-info`, `out-of-scope`
- Each scenario loads ONE instruction file and processes the entire workflow in a single LLM call
- Evaluation validates complete end-to-end flows in single test cases
- No explicit state machine - just: detect scenario → process → done

**Problem:**
This monolithic approach has limitations:
1. **Poor observability** - Can't see intermediate decisions (e.g., "serial found" vs "serial missing")
2. **Hard to debug** - When an eval fails, unclear which decision point failed
3. **Low reusability** - Can't reuse common steps (e.g., "request serial" logic duplicated)
4. **Difficult to test** - Must test entire flows, can't test individual decision points
5. **Inflexible** - Adding new branches requires creating entire new scenarios

**Desired Architecture (Step-by-Step State Machine):**
The `instructions/steps/` directory contains 8 granular step files that form a state machine:

```
START → [01-extract-serial] → decision point
                                ↓
        ┌───────────────────────┼─────────────────────┐
        ↓                       ↓                     ↓
    Serial Found         No Serial            Out of Scope
        ↓                       ↓                     ↓
[02-check-warranty]    [03d-request-serial]    [04-out-of-scope]
        ↓                       ↓                     ↓
    Decision               Send Email             Send Email
        ↓                      DONE                  DONE
    ┌───┴───┬────────┬──────────┐
    ↓       ↓        ↓          ↓
Valid    Expired  Not Found  Error
    ↓       ↓        ↓          ↓
[03a-valid] [03c-expired] [03b-not-found] [04-out-of-scope]
    ↓       ↓        ↓          ↓
Create   Offer    Ask for    Redirect
Ticket    Paid    Correct      ↓
    ↓    Repair   Serial      DONE
    ↓       ↓        ↓
[05-confirm] DONE   DONE
    ↓
Send Email
with ticket_id
    ↓
  DONE
```

Each step file:
- Has ONE clear job
- Explicitly declares which steps can come next
- Contains step-specific instructions and function definitions
- Returns a structured output that includes `NEXT_STEP` routing decision

**Benefits of Step-by-Step:**
1. **Granular observability** - See exactly which steps executed and why
2. **Easier debugging** - Pinpoint which decision failed
3. **Reusable steps** - Common logic in one place
4. **Testable decision points** - Test individual steps in isolation
5. **Flexible routing** - Add new branches by updating step routing logic
6. **Better evals** - Validate step sequence, not just final output

## User Story

**As a** developer maintaining the warranty email agent
**I want** the agent to use a step-by-step state machine architecture
**So that** I can observe intermediate decisions, debug failures more easily, and test individual steps in isolation

## Acceptance Criteria

### AC1: State Machine Orchestrator
**Given** the agent receives an email to process
**When** the orchestrator begins processing
**Then** it:
- Starts at Step 01 (`01-extract-serial.md`)
- Loads the step instruction file from `instructions/steps/`
- Passes email context to the step
- Extracts `NEXT_STEP` decision from LLM response
- Routes to the next step based on the decision
- Repeats until reaching a `DONE` state
- Logs each step transition with context

**Implementation Requirements:**
- Create new `StepOrchestrator` class in `src/guarantee_email_agent/orchestrator/step_orchestrator.py`
- Support step routing based on LLM output (parse `NEXT_STEP: {step-name}`)
- Maintain step execution history: `[(step_name, input_data, output_data, next_step)]`
- Support passing data between steps (serial_number, warranty_data, ticket_id)
- Maximum 10 steps per email (circuit breaker for infinite loops)
- Log each step transition: `logger.info("Step transition", extra={"from_step": ..., "to_step": ..., "reason": ...})`

### AC2: Step Instruction Loader
**Given** the orchestrator needs to load a step instruction
**When** requesting a step by name (e.g., `"01-extract-serial"`)
**Then** it:
- Loads the instruction file from `instructions/steps/{step-name}.md`
- Parses YAML frontmatter and markdown body
- Extracts available functions (if defined in frontmatter)
- Validates step instruction format
- Returns parsed `InstructionFile` object
- Caches loaded instructions (reuse across emails)

**Implementation Requirements:**
- Extend existing `InstructionLoader` in `src/guarantee_email_agent/instructions/loader.py`
- Add `load_step_instruction(step_name: str) -> InstructionFile` method
- Support step file path: `{project_root}/instructions/steps/{step-name}.md`
- Validate required frontmatter fields: `name`, `description`, `version`
- Use existing caching mechanism (`load_instruction_cached`)

### AC3: Refactor ScenarioDetector to StepRouter
**Given** the current `ScenarioDetector` class exists
**When** refactoring to step-based architecture
**Then**:
- **Keep** heuristic detection logic (spam keywords, short emails, warranty keywords)
- **Change** output from `ScenarioDetectionResult` to `StepRoutingResult`
- **Replace** scenario names (`valid-warranty`, `missing-info`) with step names (`01-extract-serial`)
- **Always** route to Step 01 as the entry point (let Step 01 make the first decision)
- Optionally use heuristics to skip to Step 02 if serial found via regex

**Implementation Requirements:**
- Rename `scenario_detector.py` → `step_router.py`
- Rename class: `ScenarioDetector` → `StepRouter`
- Update `detect_scenario()` → `route_to_initial_step()`
- Return `StepRoutingResult(step_name="01-extract-serial", confidence=1.0, routing_method="default")`
- Keep LLM fallback for ambiguous cases (optional optimization)

### AC4: Update ResponseGenerator for Step Mode
**Given** the `ResponseGenerator` currently works with monolithic scenarios
**When** generating responses in step mode
**Then** it:
- Loads step instruction instead of scenario instruction
- Builds system message from step instruction body
- Calls LLM with step-specific guidance
- Parses LLM response for `NEXT_STEP` decision
- Returns `StepExecutionResult(next_step, response_text, metadata)`
- Supports both function calling and text response modes

**Implementation Requirements:**
- Add new method: `generate_step_response(step_name, email_content, context_data) -> StepExecutionResult`
- Parse LLM response for routing decision (regex: `NEXT_STEP:\s*(\S+)`)
- Extract `SERIAL:`, `REASON:`, and other structured outputs
- Maintain backward compatibility with monolithic scenario mode (for gradual migration)

### AC5: Refactor Eval Framework for Step Validation
**Given** current evals validate end-to-end monolithic flows
**When** refactoring evals for step-by-step architecture
**Then** evals:
- Validate the **sequence of steps executed** (e.g., `[01-extract-serial, 02-check-warranty, 03a-valid-warranty, 05-send-confirmation]`)
- Check step transitions are correct based on data (e.g., if serial found, must go to 02, not 03d)
- Validate function calls made at each step (e.g., `check_warranty` only called in Step 02)
- Allow step-level assertions (e.g., "Step 01 should extract serial SN12345")
- Maintain backward compatibility with existing eval YAML format

**Eval YAML Format (Extended):**
```yaml
scenario_id: valid_warranty_step_001
description: "Step-by-step validation: valid warranty flow"
category: valid-warranty

input:
  email: {...}
  mock_function_responses: {...}

expected_output:
  # NEW: Step sequence validation
  expected_steps:
    - step_name: "01-extract-serial"
      output_contains:
        - "NEXT_STEP: 02-check-warranty"
        - "SERIAL: SN12345"
    - step_name: "02-check-warranty"
      function_call: "check_warranty"
      function_args: {serial_number: "SN12345"}
      output_contains:
        - "NEXT_STEP: 03a-valid-warranty"
    - step_name: "03a-valid-warranty"
      function_call: "create_ticket"
      output_contains:
        - "NEXT_STEP: 05-send-confirmation"
    - step_name: "05-send-confirmation"
      function_call: "send_email"
      output_contains:
        - "TKT-12345"

  # EXISTING: Backward-compatible fields
  scenario_instruction_used: "multi-step"  # Special marker
  processing_time_ms: 60000
  expected_function_calls: [...]  # Still validate overall function calls
```

**Implementation Requirements:**
- Update `EvalTestCase` model in `src/guarantee_email_agent/eval/models.py`:
  - Add `expected_steps: List[ExpectedStepExecution]` field
  - Make backward compatible with existing evals (if `expected_steps` missing, skip step validation)
- Update `EvalRunner.validate_output()`:
  - Add step sequence validation logic
  - Compare `actual_steps` (from orchestrator history) vs `expected_steps`
  - Validate step transitions based on data
  - Report which step failed if mismatch
- Create new validator: `src/guarantee_email_agent/eval/step_validator.py`
  - `validate_step_sequence(expected, actual) -> (passed, failures)`
  - `validate_step_transitions(steps, context_data) -> (passed, failures)`

### AC6: Migrate Existing Evals to Step-Based Format
**Given** 12 existing eval test cases in `evals/scenarios/`
**When** migrating to step-based architecture
**Then**:
- Keep all 12 existing eval files (don't delete)
- Add `expected_steps` section to each eval
- Map monolithic scenarios to step sequences:
  - `valid-warranty` → `[01, 02, 03a, 05]`
  - `invalid-warranty` (expired) → `[01, 02, 03c]`
  - `device-not-found` → `[01, 02, 03b]`
  - `missing-info` → `[01, 03d]`
  - `out-of-scope` → `[01, 04]`
- All 12 evals must pass with 100% pass rate (12/12 passing)

**Implementation Requirements:**
- Update each YAML file in `evals/scenarios/` with `expected_steps`
- Run full eval suite: `uv run python -m guarantee_email_agent eval`
- Achieve 100% pass rate (12/12 passing) - Zero tolerance for regression
- Document step mapping in eval comments

### AC7: Backward Compatibility Mode
**Given** the refactoring introduces breaking changes
**When** deploying the step-based architecture
**Then**:
- Support **dual mode** via config flag: `use_step_orchestrator: bool`
- Default to `use_step_orchestrator: true` (new behavior)
- Allow fallback to `use_step_orchestrator: false` (legacy monolithic mode)
- Gracefully handle both modes in CLI and eval runner
- Remove legacy mode after 2 weeks if no issues found
- **Rollback trigger**: If >5% of production emails fail, immediately revert to `use_step_orchestrator: false`

**Implementation Requirements:**
- Add config field in `config.yaml`: `orchestration.use_step_orchestrator: true`
- Update `AgentConfig` schema in `src/guarantee_email_agent/config/schema.py`
- Update `EmailProcessor` to choose orchestrator based on config:
  ```python
  if self.config.orchestration.use_step_orchestrator:
      result = await self.step_orchestrator.process(email)
  else:
      result = await self._legacy_process(email)  # Old monolithic path
  ```

### AC8: Logging and Observability
**Given** the step-based architecture runs in production
**When** processing emails
**Then** logs include:
- **Step transitions**: `"Step transition: 01-extract-serial → 02-check-warranty (reason: serial found)"`
- **Step execution time**: `"Step completed: 01-extract-serial (120ms)"`
- **Step output summary**: `"Step output: NEXT_STEP=02-check-warranty, SERIAL=SN12345"`
- **Full step history** in final log: `"Email processing complete: 4 steps executed: [01, 02, 03a, 05]"`
- All customer data at DEBUG level only (per NFR14)

**Implementation Requirements:**
- Add structured logging in `StepOrchestrator`:
  ```python
  logger.info("Step transition", extra={
      "from_step": current_step,
      "to_step": next_step,
      "reason": routing_reason,
      "serial_number": serial_number  # DEBUG level only
  })
  ```
- Log step execution time for performance monitoring
- Final summary log with full step sequence

## Technical Design

### New Files to Create

1. **`src/guarantee_email_agent/orchestrator/__init__.py`** - New package for orchestration logic
2. **`src/guarantee_email_agent/orchestrator/step_orchestrator.py`** - Main state machine orchestrator
3. **`src/guarantee_email_agent/orchestrator/models.py`** - Step execution models (`StepExecutionResult`, `StepRoutingResult`, `StepContext`)
4. **`src/guarantee_email_agent/eval/step_validator.py`** - Step sequence validation logic

### Files to Modify

1. **`src/guarantee_email_agent/email/scenario_detector.py`** → Rename to `step_router.py`, refactor to route to Step 01
2. **`src/guarantee_email_agent/llm/response_generator.py`** - Add `generate_step_response()` method
3. **`src/guarantee_email_agent/instructions/loader.py`** - Add `load_step_instruction()` method
4. **`src/guarantee_email_agent/email/processor.py`** - Integrate `StepOrchestrator`, support dual mode
5. **`src/guarantee_email_agent/eval/runner.py`** - Add step validation logic
6. **`src/guarantee_email_agent/eval/models.py`** - Add `expected_steps` field
7. **`src/guarantee_email_agent/config/schema.py`** - Add `orchestration.use_step_orchestrator` field
8. **`config.yaml`** - Add `orchestration.use_step_orchestrator: true`
9. **All 12 eval files in `evals/scenarios/`** - Add `expected_steps` section

### Files to Keep (No Changes)

1. **`instructions/steps/*.md`** - Step instruction files (already exist, ready to use)
   - Naming convention: `{step-number}-{description}.md` (e.g., `01-extract-serial.md`, `03a-valid-warranty.md`)
   - 8 step files total: 01, 02, 03a, 03b, 03c, 03d, 04, 05
2. **`instructions/WORKFLOW.md`** - Step-by-step workflow documentation (reference for implementation)
3. **`src/guarantee_email_agent/email/serial_extractor.py`** - Serial extraction logic (reused in Step 01)
4. **`src/guarantee_email_agent/llm/function_dispatcher.py`** - Function calling (reused per step)

### High-Level Flow (Post-Refactor)

```
EmailProcessor.process_email(email)
  ↓
StepOrchestrator.orchestrate(email)
  ↓
  current_step = "01-extract-serial"  # Entry point
  ↓
  LOOP until DONE:
    ↓
    1. Load step instruction: load_step_instruction(current_step)
    ↓
    2. Build step context: {email, serial_number, warranty_data, ticket_id}
    ↓
    3. Call LLM: generate_step_response(current_step, context)
    ↓
    4. Parse response: extract NEXT_STEP, SERIAL, other outputs
    ↓
    5. Execute functions (if step defines functions): check_warranty, create_ticket, send_email
    ↓
    6. Log step transition: current_step → next_step
    ↓
    7. Update context with new data (warranty_data, ticket_id)
    ↓
    8. Set current_step = next_step
    ↓
  END LOOP (when NEXT_STEP = "DONE")
  ↓
  Return step_history + final_output
```

## Testing Strategy

### Unit Tests
- `tests/orchestrator/test_step_orchestrator.py`:
  - Test step loading and routing
  - Test context passing between steps
  - Test infinite loop prevention (max 10 steps)
  - Test graceful error handling (step not found, invalid routing)
- `tests/eval/test_step_validator.py`:
  - Test step sequence validation
  - Test step transition validation
  - Test backward compatibility with old eval format

### Integration Tests
- `tests/integration/test_step_workflow.py`:
  - Test complete step flow: `[01, 02, 03a, 05]` (valid warranty)
  - Test branching: `[01, 03d]` (missing serial)
  - Test error handling: `[01, 04]` (out of scope)

### Eval Tests
- Run full eval suite with all 12 test cases
- Target: 100% pass rate (12/12 passing)
- Validate step sequences match expected flows

### Manual Testing
- Enable `use_step_orchestrator: true` in config
- Process sample emails, observe step transitions in logs
- Verify step-by-step execution matches WORKFLOW.md diagram
- Test backward compatibility: disable flag, verify legacy mode works

## Migration Plan

### Phase 1: Create Step Orchestrator (Day 1-2)
- [ ] Create `StepOrchestrator` class with step routing logic
- [ ] Add `load_step_instruction()` to `InstructionLoader`
- [ ] Create step execution models (`StepExecutionResult`, `StepContext`)
- [ ] Write unit tests for orchestrator
- [ ] Verify step loading works with existing `instructions/steps/*.md` files

### Phase 2: Refactor Detection to Routing (Day 2-3)
- [ ] Rename `scenario_detector.py` → `step_router.py`
- [ ] Update routing logic to always return Step 01 as entry point
- [ ] Update `ResponseGenerator` with `generate_step_response()`
- [ ] Add response parsing for `NEXT_STEP`, `SERIAL`, etc.
- [ ] Write unit tests for step response generation

### Phase 3: Integrate with EmailProcessor (Day 3)
- [ ] Add `use_step_orchestrator` config flag
- [ ] Update `EmailProcessor` to support dual mode (step vs legacy)
- [ ] Add step transition logging
- [ ] Test end-to-end step execution with sample email
- [ ] Verify step transitions logged correctly with all required fields (from_step, to_step, reason)

### Phase 4: Refactor Eval Framework (Day 4)
- [ ] Update `EvalTestCase` model with `expected_steps` field
- [ ] Create `step_validator.py` with step validation logic
- [ ] Update `EvalRunner` to validate step sequences
- [ ] Write unit tests for step validation

### Phase 5: Migrate Evals and Verify (Day 5)
- [ ] Add `expected_steps` to all 12 eval YAML files
- [ ] Run full eval suite: `uv run python -m guarantee_email_agent eval`
- [ ] Debug and fix any failing evals
- [ ] Achieve 100% pass rate (12/12 passing)
- [ ] Document step sequences in eval comments

### Phase 6: Cleanup and Documentation (Day 5)
- [ ] Update README with step-based architecture explanation
- [ ] Add developer documentation: "How Step Routing Works"
- [ ] Remove `use_step_orchestrator: false` fallback (only after 2 weeks in prod with <5% failure rate)
- [ ] Archive legacy scenario instruction files (keep for reference)

## Definition of Done

- [ ] All 8 acceptance criteria implemented and tested (see AC1-AC8 above)
- [ ] `StepOrchestrator` successfully executes step-by-step flows
- [ ] All 12 existing evals updated with `expected_steps` and passing (100% pass rate = 12/12)
- [ ] Step transitions logged with context at INFO level (per AC8)
- [ ] Backward compatibility mode works (can toggle via config per AC7)
- [ ] Unit test coverage ≥80% for new orchestrator code
- [ ] Integration tests validate complete step flows
- [ ] Code reviewed and approved
- [ ] Migration Plan Phase 6 completed (documentation + cleanup)
- [ ] No regressions in existing functionality (verified via full eval suite)

## Edge Cases & Error Handling

1. **Infinite loop prevention**: Max 10 steps per email, then fail with error
2. **Invalid step routing**: If `NEXT_STEP` references non-existent step, log error and route to graceful-degradation
3. **LLM timeout during step**: Retry step up to 3 times, then mark email as failed
4. **Step instruction not found**: Log error, route to graceful-degradation scenario
5. **Function call failure mid-flow**: Log error, allow step to decide next action (e.g., Step 02 fails → route to 04-out-of-scope)
6. **Missing context data**: If step expects `serial_number` but not in context, log warning and proceed (let LLM handle missing data)

## Non-Functional Requirements

- **Performance**: Step-based orchestration adds max 200ms overhead per email (acceptable for observability gains)
- **Determinism**: Maintain temperature=0 and pinned model for 99% eval pass rate
- **Observability**: Every step transition logged with context (NFR-compliant structured logging)
- **Backward Compatibility**: Legacy mode must work identically to current behavior (zero regression)
- **Scalability**: Step caching prevents repeated file I/O (instructions loaded once, reused)

## Success Metrics

- ✅ 100% eval pass rate (12/12 passing) with step validation
- ✅ Step execution history visible in logs for every email
- ✅ Average processing time increase <200ms per email
- ✅ Zero regressions in existing functionality (legacy mode passes all tests)
- ✅ Developer feedback: "Debugging failures is 10x easier with step logs"

## Follow-Up Stories

- **Story 5.2**: Add new step for "warranty extension offer" (demonstrates easy branching)
- **Story 5.3**: Implement step-level retry logic (retry individual step vs entire email)
- **Story 5.4**: Create admin dashboard showing step execution statistics (which steps are most common, where failures occur)
- **Story 5.5**: A/B test step routing strategies (heuristic vs LLM routing for Step 01)

---

**Story Ready for Development**: Yes ✅
**Dependencies Resolved**: Story 4.6 (Refactor MCP to Simple Tools) completed
**Risks**: Medium - Large refactoring with eval migration, but backward compatibility mode mitigates deployment risk
**Estimated Effort**: 5 days (2 days core orchestrator, 2 days eval refactor, 1 day testing/migration)
