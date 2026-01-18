# Story 4.5: MCP Tool-Calling Architecture with LLM Decision Making

**Epic:** Epic 4 - Evaluation Framework
**Status:** Draft
**Priority:** High
**Estimated Effort:** 8-13 points (Large)
**Created:** 2026-01-18
**Dependencies:** Story 4.1 (Eval Framework), Story 3.6 (Email Processing Pipeline)

## Problem Statement

The current architecture hardcodes which MCP clients to call in the Python code (processor.py). This creates several limitations:

1. **Inflexible scenario handling**: All warranty inquiries call the same warranty API regardless of scenario needs
2. **No per-scenario tool selection**: Can't specify different MCP tools for different scenarios
3. **Missed LLM capabilities**: Not leveraging LLM's reasoning to decide when/which tools to use
4. **Scalability issues**: Adding new scenarios or tools requires Python code changes

**Example of current limitation:**
- `missing-info` scenario shouldn't call warranty API (no serial number), but architecture requires it
- `valid-warranty` scenario needs both warranty check + ticket creation
- `invalid-warranty` scenario needs only warranty check (no ticket)
- Future scenarios (e.g., `product-inquiry`) might need different tools (knowledge base, CRM)

## Desired Outcome

Implement true MCP tool-calling architecture where:

1. **LLM decides which tools to call** based on scenario instructions and email content
2. **Scenario instructions declare available tools** in YAML frontmatter
3. **Tool execution is handled by MCP protocol** (mocked for eval, real for production)
4. **Eval framework tests tool-calling behavior** with deterministic mock responses
5. **Agent uses same architecture** for both eval (mocks) and production (real MCP servers)

**Success Criteria:**
- Anthropic's tool-calling API integrated with scenario-specific tool definitions
- LLM autonomously decides when to call `check_warranty`, `create_ticket`, etc.
- Scenario instructions specify available tools without Python code changes
- Eval tests validate correct tool usage per scenario
- Mock MCP clients return deterministic data for eval
- All existing eval tests pass with new architecture
- Pass rate ≥99% maintained (NFR1)

## User Story

**As a** warranty email agent developer
**I want** the LLM to decide which MCP tools to call based on scenario instructions
**So that** I can add new scenarios and tools without changing Python code, and leverage LLM reasoning for intelligent tool selection

## Acceptance Criteria

### AC1: Scenario Instructions Declare Available Tools
- [ ] Scenario instruction YAML frontmatter includes `available_tools` list
- [ ] Tool definitions include: tool name, description, parameter schema
- [ ] Example: `valid-warranty.md` declares `warranty_api.check_warranty` and `ticketing_system.create_ticket`
- [ ] Example: `missing-info.md` declares no tools (empty list)
- [ ] Tool schemas follow Anthropic's tool definition format

**Example YAML frontmatter:**
```yaml
---
name: valid-warranty
description: Response for valid warranty inquiries
available_tools:
  - name: check_warranty
    description: Check warranty status for a product serial number
    input_schema:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number to check
      required: [serial_number]

  - name: create_ticket
    description: Create support ticket for valid warranty RMA
    input_schema:
      type: object
      properties:
        serial_number:
          type: string
        customer_email:
          type: string
        priority:
          type: string
          enum: [low, normal, high, urgent]
      required: [serial_number, customer_email]
---
```

### AC2: LLM Provider Supports Tool Calling
- [ ] `AnthropicProvider` implements `create_message_with_tools()` method
- [ ] Supports Anthropic's tool-calling API (Claude 3.5+)
- [ ] Handles tool use requests from LLM
- [ ] Executes tool calls via MCP client dispatch
- [ ] Returns tool results to LLM for final response generation
- [ ] Supports multi-turn tool calling (LLM → tool → LLM → tool → response)
- [ ] Temperature=0 for deterministic tool selection

**API signature:**
```python
async def create_message_with_tools(
    self,
    system_prompt: str,
    user_prompt: str,
    available_tools: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> ToolCallingResult:
    """Generate response with tool calling support.

    Returns:
        ToolCallingResult with:
        - response_text: Final LLM response
        - tool_calls: List of tools called (name, inputs, outputs)
        - stop_reason: "end_turn" or "tool_use"
    """
```

### AC3: MCP Client Dispatcher Routes Tool Calls
- [ ] `MCPClientDispatcher` class created to route tool calls to correct client
- [ ] Maps tool names to MCP client methods:
  - `check_warranty` → `WarrantyMCPClient.check_warranty()`
  - `create_ticket` → `TicketingMCPClient.create_ticket()`
  - `send_email` → `GmailMCPClient.send_email()`
- [ ] Validates tool input parameters against schema
- [ ] Returns structured tool results
- [ ] Handles tool execution errors gracefully
- [ ] Logs all tool calls with input/output for debugging

**Implementation:**
```python
class MCPClientDispatcher:
    """Dispatch tool calls to appropriate MCP clients."""

    def __init__(
        self,
        warranty_client: WarrantyMCPClient,
        ticketing_client: TicketingMCPClient,
        gmail_client: GmailMCPClient
    ):
        self.clients = {
            "check_warranty": warranty_client.check_warranty,
            "create_ticket": ticketing_client.create_ticket,
            "send_email": gmail_client.send_email,
        }

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool call and return result."""
        if tool_name not in self.clients:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool_func = self.clients[tool_name]
        result = await tool_func(**tool_input)

        return {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": result
        }
```

### AC4: Email Processor Uses Tool-Calling Architecture
- [ ] `EmailProcessor.process_email()` refactored to use tool-calling
- [ ] Loads scenario instruction with tool definitions
- [ ] Passes available tools to LLM provider
- [ ] Executes tool calls via MCP dispatcher
- [ ] Handles multi-turn tool calling loop
- [ ] Maintains same processing steps (parse → extract → detect → generate)
- [ ] Backwards compatible with scenarios that don't use tools

**Processing flow:**
```python
# Step 1-3: Parse, Extract, Detect (unchanged)
email = self.parser.parse_email(raw_email)
serial_result = await self.extractor.extract_serial_number(email)
detection_result = await self.detector.detect_scenario(email, serial_result)

# Step 4: Load scenario with tool definitions
scenario_instruction = self.router.select_scenario(detection_result.scenario_name)
available_tools = scenario_instruction.get_available_tools()

# Step 5: Generate response with tool calling
tool_result = await self.response_generator.generate_with_tools(
    scenario_instruction=scenario_instruction,
    email_content=email.body,
    serial_number=serial_result.serial_number,
    available_tools=available_tools
)

# Step 6: Send response (tool might have already sent it)
if not tool_result.email_sent_by_tool:
    await self.gmail_client.send_email(...)
```

### AC5: Eval Framework Tests Tool-Calling Behavior
- [ ] Eval test cases specify expected tool calls
- [ ] `EvalExpectedOutput` includes `expected_tool_calls` field
- [ ] Validation checks: correct tools called, correct parameters, correct order
- [ ] Mock clients return deterministic responses for eval
- [ ] Tool call history tracked in eval results
- [ ] Failed tool calls logged in eval failures

**Eval test case format:**
```yaml
scenario_id: valid_warranty_002
description: Valid warranty with tool calling

input:
  email:
    subject: "RMA request"
    body: "I need RMA for serial number SN12345"
    from: "customer@example.com"
    received: "2026-01-18T10:00:00Z"

  # Mock tool responses
  mock_tool_responses:
    check_warranty:
      serial_number: "SN12345"
      status: "valid"
      expiration_date: "2025-12-31"

expected_output:
  email_sent: true
  ticket_created: true

  # NEW: Expected tool calls
  expected_tool_calls:
    - tool_name: check_warranty
      tool_input:
        serial_number: "SN12345"
      tool_output_contains:
        status: "valid"

    - tool_name: create_ticket
      tool_input_contains:
        serial_number: "SN12345"
        customer_email: "customer@example.com"

  response_body_contains:
    - "warranty is valid"
    - "2025-12-31"

  scenario_instruction_used: "valid-warranty"
```

### AC6: All Scenarios Support Tool-Calling
- [ ] `valid-warranty.md` updated with `check_warranty` + `create_ticket` tools
- [ ] `invalid-warranty.md` updated with `check_warranty` tool only
- [ ] `missing-info.md` has empty tools list (no tools needed)
- [ ] `graceful-degradation.md` has fallback tools if applicable
- [ ] All scenario instructions include tool usage guidance in `<objective>`
- [ ] Instruction templates updated with tool-calling examples

### AC7: Backwards Compatibility and Migration
- [ ] Existing eval tests continue to pass (with tool-calling disabled flag)
- [ ] `ResponseGenerator` supports both old and new modes
- [ ] Migration guide documents how to convert scenarios to tool-calling
- [ ] Performance benchmarks show <5% overhead from tool-calling
- [ ] All NFRs still met (NFR7: <60s processing, NFR1: ≥99% pass rate)

## Technical Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Scenario Instruction (valid-warranty.md)                       │
│  - Declares available_tools: [check_warranty, create_ticket]    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  ResponseGenerator.generate_with_tools()                        │
│  - Builds system prompt with scenario instruction               │
│  - Builds user prompt with email + serial number                │
│  - Passes tool definitions to LLM provider                      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  AnthropicProvider.create_message_with_tools()                  │
│  - Calls Claude API with tools parameter                        │
│  - LLM decides: "I need to check warranty for SN12345"          │
│  - Returns tool_use request                                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  MCPClientDispatcher.execute_tool("check_warranty", {...})      │
│  - Routes to WarrantyMCPClient.check_warranty(serial="SN12345") │
│  - Returns: {status: "valid", expiration_date: "2025-12-31"}    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  AnthropicProvider (continues)                                  │
│  - Sends tool result back to LLM                                │
│  - LLM decides: "I need to create ticket"                       │
│  - Returns another tool_use request                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  MCPClientDispatcher.execute_tool("create_ticket", {...})       │
│  - Routes to TicketingMCPClient.create_ticket(...)              │
│  - Returns: {ticket_id: "TKT-123"}                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  AnthropicProvider (final turn)                                 │
│  - Sends ticket result back to LLM                              │
│  - LLM generates final response text                            │
│  - Returns: "Your warranty is valid until 2025-12-31..."        │
└─────────────────────────────────────────────────────────────────┘
```

### File Changes

**New Files:**
1. `src/guarantee_email_agent/integrations/mcp/dispatcher.py` - MCP client dispatcher
2. `src/guarantee_email_agent/llm/tool_calling.py` - Tool-calling models and utilities
3. `src/guarantee_email_agent/instructions/tool_loader.py` - Load tool definitions from YAML
4. `tests/llm/test_tool_calling.py` - Unit tests for tool-calling
5. `tests/integrations/test_mcp_dispatcher.py` - Dispatcher tests
6. `docs/architecture/mcp-tool-calling.md` - Architecture documentation

**Modified Files:**
1. `src/guarantee_email_agent/llm/provider.py`
   - Add `create_message_with_tools()` to `AnthropicProvider`
   - Add tool-calling loop logic

2. `src/guarantee_email_agent/llm/response_generator.py`
   - Add `generate_with_tools()` method
   - Support both old and new generation modes

3. `src/guarantee_email_agent/email/processor.py`
   - Refactor to use tool-calling architecture
   - Add tool call tracking for logging

4. `src/guarantee_email_agent/instructions/loader.py`
   - Parse `available_tools` from YAML frontmatter
   - Validate tool schemas

5. `src/guarantee_email_agent/eval/models.py`
   - Add `expected_tool_calls` to `EvalExpectedOutput`
   - Add `tool_calls` to `EvalResult`

6. `src/guarantee_email_agent/eval/runner.py`
   - Track tool calls during eval execution
   - Validate tool usage against expectations

7. `instructions/scenarios/valid-warranty.md`
   - Add `available_tools` to frontmatter
   - Update objective with tool usage guidance

8. `instructions/scenarios/invalid-warranty.md`
   - Add `check_warranty` tool only

9. `instructions/scenarios/missing-info.md`
   - Set `available_tools: []` (no tools needed)

### Data Models

```python
# src/guarantee_email_agent/llm/tool_calling.py

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ToolDefinition(BaseModel):
    """Tool definition for LLM tool-calling."""
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema for tool inputs

class ToolCall(BaseModel):
    """Record of a tool call execution."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    execution_time_ms: int
    success: bool
    error_message: Optional[str] = None

class ToolCallingResult(BaseModel):
    """Result from LLM generation with tool calling."""
    response_text: str
    tool_calls: List[ToolCall]
    stop_reason: str  # "end_turn" or "tool_use"
    total_tokens: int
    tool_call_count: int
```

### Tool-Calling Implementation Pattern

```python
# Anthropic's tool-calling API pattern

async def create_message_with_tools(
    self,
    system_prompt: str,
    user_prompt: str,
    available_tools: List[ToolDefinition],
    max_tokens: int = 2048,
    temperature: float = 0
) -> ToolCallingResult:
    """Generate response with tool calling support."""

    messages = [{"role": "user", "content": user_prompt}]
    tool_calls = []

    # Convert tools to Anthropic format
    tools = [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema
        }
        for tool in available_tools
    ]

    # Tool-calling loop (max 10 iterations to prevent infinite loops)
    for iteration in range(10):
        response = self.client.messages.create(
            model=self.config.model,
            system=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # LLM finished - extract final text
            final_text = self._extract_text_from_response(response)
            return ToolCallingResult(
                response_text=final_text,
                tool_calls=tool_calls,
                stop_reason="end_turn",
                total_tokens=response.usage.total_tokens,
                tool_call_count=len(tool_calls)
            )

        elif response.stop_reason == "tool_use":
            # LLM wants to use a tool
            tool_use_block = self._extract_tool_use(response)
            tool_name = tool_use_block["name"]
            tool_input = tool_use_block["input"]

            # Execute tool via dispatcher
            start_time = time.time()
            try:
                tool_output = await self.mcp_dispatcher.execute_tool(
                    tool_name=tool_name,
                    tool_input=tool_input
                )
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Record successful tool call
                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=tool_output,
                    execution_time_ms=execution_time_ms,
                    success=True
                ))

                # Add tool result to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use_block["id"],
                        "content": json.dumps(tool_output)
                    }]
                })

            except Exception as e:
                # Tool execution failed
                execution_time_ms = int((time.time() - start_time) * 1000)
                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output={},
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(e)
                ))

                # Return error to LLM
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use_block["id"],
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    }]
                })

        else:
            raise ValueError(f"Unexpected stop_reason: {response.stop_reason}")

    # Max iterations reached
    raise LLMError(
        message="Tool-calling loop exceeded max iterations (10)",
        code="tool_calling_max_iterations",
        details={"tool_calls": len(tool_calls)}
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
available_tools:
  - name: check_warranty
    description: Check warranty status for a product serial number. Returns warranty status, expiration date, and coverage details.
    input_schema:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number to check warranty for
      required: [serial_number]

  - name: create_ticket
    description: Create a support ticket for valid warranty RMA claims. Should only be called after confirming warranty is valid.
    input_schema:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number
        customer_email:
          type: string
          description: Customer email address
        customer_name:
          type: string
          description: Customer name
        priority:
          type: string
          enum: [low, normal, high, urgent]
          description: Ticket priority level
        category:
          type: string
          description: Ticket category (e.g., warranty_claim, rma)
        subject:
          type: string
          description: Ticket subject line
      required: [serial_number, customer_email, priority, category]
---

<objective>
Generate a professional response IN POLISH for valid warranty inquiries.

**Tool Usage:**
1. First, call check_warranty() with the serial number to verify status and get expiration date
2. If warranty is valid, call create_ticket() to create RMA tracking ticket
3. Include warranty details (expiration date) and ticket confirmation in response
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
available_tools: []  # No tools needed - just generate helpful response
---

<objective>
Politely request IN POLISH the missing serial number.

**Tool Usage:**
No tools needed for this scenario. Generate a helpful response asking for the serial number.
</objective>

[Rest of instruction unchanged...]
```

## Implementation Plan

### Phase 1: Core Tool-Calling Infrastructure (3-5 days)
**Tasks:**
1. Create `tool_calling.py` with data models
2. Create `MCPClientDispatcher` class
3. Add `create_message_with_tools()` to `AnthropicProvider`
4. Write unit tests for tool-calling logic
5. Test with simple single-tool scenario

**Deliverables:**
- Tool-calling models defined
- Dispatcher routing tool calls correctly
- Anthropic provider executing tool-calling loop
- Unit tests passing

### Phase 2: Scenario Tool Definitions (2-3 days)
**Tasks:**
1. Update `InstructionLoader` to parse `available_tools` from YAML
2. Create `ToolDefinitionLoader` to validate tool schemas
3. Update all scenario instructions with tool definitions
4. Add tool usage guidance to instruction objectives

**Deliverables:**
- Scenario instructions declare tools
- Tool definitions validated against schemas
- All 4 scenarios updated (valid, invalid, missing, degradation)

### Phase 3: Email Processor Integration (3-4 days)
**Tasks:**
1. Refactor `EmailProcessor.process_email()` to use tool-calling
2. Update `ResponseGenerator.generate_with_tools()`
3. Wire up MCP dispatcher with existing clients
4. Add tool call logging and tracking
5. Maintain backwards compatibility

**Deliverables:**
- Email processor uses tool-calling architecture
- Tool calls logged with input/output
- Existing functionality preserved
- Performance benchmarks meet targets

### Phase 4: Eval Framework Updates (2-3 days)
**Tasks:**
1. Add `expected_tool_calls` to eval test case schema
2. Update `EvalRunner` to track and validate tool calls
3. Update `EvalReporter` to show tool call results
4. Create new eval test cases with tool-calling expectations
5. Migrate existing eval tests to new format

**Deliverables:**
- Eval validates tool usage
- Tool call history in eval results
- All eval tests pass with tool-calling
- Pass rate ≥99% maintained

### Phase 5: Documentation and Migration (1-2 days)
**Tasks:**
1. Write MCP tool-calling architecture documentation
2. Create migration guide for scenarios
3. Update README with tool-calling examples
4. Document tool definition format and best practices
5. Add troubleshooting guide for tool-calling issues

**Deliverables:**
- Architecture docs complete
- Migration guide published
- Examples documented
- Team trained on new architecture

## Testing Strategy

### Unit Tests
- `test_tool_calling.py`: ToolDefinition, ToolCall, ToolCallingResult models
- `test_mcp_dispatcher.py`: Dispatcher routing, error handling
- `test_anthropic_tool_calling.py`: Tool-calling loop, multi-turn conversations
- `test_tool_loader.py`: YAML parsing, schema validation

### Integration Tests
- `test_processor_with_tools.py`: End-to-end processing with tool-calling
- `test_eval_tool_validation.py`: Eval framework validates tool usage
- `test_scenario_tool_integration.py`: Each scenario uses correct tools

### Eval Tests
- Create 5+ new eval test cases per scenario with `expected_tool_calls`
- Test cases cover:
  - Single tool call (check_warranty only)
  - Multiple tool calls (check_warranty + create_ticket)
  - No tool calls (missing-info scenario)
  - Tool call with error handling
  - Tool call parameter validation

### Performance Tests
- Measure overhead of tool-calling vs direct calls
- Ensure <5% performance impact
- Validate NFR7 still met (<60s p95 processing time)
- Check LLM token usage increase

## Non-Functional Requirements Impact

**NFR1 (Pass Rate ≥99%):** Must maintain after refactor
**NFR7 (Processing Time <60s):** Tool-calling adds ~1-3s per tool, monitor closely
**NFR11 (LLM Timeout 15s):** Each LLM call in tool loop has 15s timeout
**NFR12 (Multi-Provider):** Only Anthropic supports tool-calling initially (Gemini future)
**NFR5 (No Silent Failures):** Log all tool calls, inputs, outputs, errors
**NFR25 (Context for Troubleshooting):** Tool call history aids debugging

## Risks and Mitigations

### Risk 1: LLM Makes Incorrect Tool Calls
**Likelihood:** Medium
**Impact:** High (wrong warranty checks, missed tickets)
**Mitigation:**
- Use temperature=0 for deterministic tool selection
- Provide clear tool descriptions and examples in scenario instructions
- Eval tests validate correct tool usage
- Add tool call validation in dispatcher

### Risk 2: Performance Degradation
**Likelihood:** Medium
**Impact:** Medium (slower processing, higher costs)
**Mitigation:**
- Benchmark tool-calling overhead
- Set max iterations limit (10) to prevent infinite loops
- Cache tool results where applicable
- Monitor LLM token usage

### Risk 3: Complex Multi-Turn Debugging
**Likelihood:** High
**Impact:** Medium (harder to troubleshoot)
**Mitigation:**
- Comprehensive logging of tool calls and LLM responses
- Eval framework shows full tool call history
- Add debug mode to log full conversation turns
- Create troubleshooting runbook

### Risk 4: Breaking Existing Functionality
**Likelihood:** Medium
**Impact:** High (regression in working scenarios)
**Mitigation:**
- Maintain backwards compatibility flag
- All existing eval tests must pass
- Gradual migration per scenario
- Extensive integration testing

### Risk 5: Gemini Doesn't Support Tool-Calling (Yet)
**Likelihood:** Low (Gemini 2.0 supports function calling)
**Impact:** Medium (limits multi-provider support)
**Mitigation:**
- Implement Anthropic first, abstract tool-calling interface
- Add GeminiProvider tool-calling in follow-up story
- Document provider-specific limitations
- Fallback to non-tool mode for unsupported providers

## Success Metrics

- [ ] All 4 scenarios converted to tool-calling architecture
- [ ] ≥99% eval pass rate maintained (NFR1)
- [ ] P95 processing time <60s maintained (NFR7)
- [ ] Tool-calling overhead <5% vs baseline
- [ ] Zero regressions in existing eval tests
- [ ] 100% of tool calls logged with input/output
- [ ] Documentation complete with migration guide
- [ ] Team trained and comfortable with new architecture

## Follow-Up Stories

**Story 4.6:** Gemini Provider Tool-Calling Support
**Story 4.7:** Real MCP Server Implementation (Warranty API)
**Story 4.8:** Advanced Tool-Calling (Parallel Tool Execution)
**Story 4.9:** Tool-Calling Monitoring and Analytics
**Story 5.1:** Production MCP Server Deployment

## References

- [Anthropic Tool Use Documentation](https://docs.anthropic.com/claude/docs/tool-use)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Story 4.1: Eval Framework with Mocked MCP Clients](./story-4.1-eval-framework-and-mocked-mcp-clients.md)
- [Story 3.6: Email Processing Pipeline Integration](./story-3.6-email-processing-pipeline-integration.md)

## Notes

- This is a significant architectural change that affects multiple components
- Phased implementation recommended to reduce risk
- Consider feature flag for gradual rollout
- Tool-calling enables future extensibility (new tools, new scenarios)
- Foundation for production MCP server integration (Epic 5)
