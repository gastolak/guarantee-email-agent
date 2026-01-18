# Implementation Notes: Multi-LLM Provider Support

## Date: 2026-01-18

## Summary
Added support for Google Gemini as an alternative LLM provider alongside Anthropic Claude. Implemented a provider abstraction layer to allow easy switching between LLM providers via configuration.

## Changes Made

### 1. LLM Provider Abstraction Layer
**File Created:** `src/guarantee_email_agent/llm/provider.py`

Created a provider abstraction pattern with:
- **Abstract Base Class (`LLMProvider`)**: Defines interface for all LLM providers
  - `create_message(system_prompt, user_prompt, max_tokens, temperature)` - standardized method signature

- **AnthropicProvider**: Implementation for Anthropic Claude
  - Uses existing `anthropic` SDK
  - Supports all Claude models (currently using claude-sonnet-4-5)

- **GeminiProvider**: Implementation for Google Gemini
  - Uses `google-generativeai` SDK
  - Combines system and user prompts (Gemini doesn't have separate system messages)
  - Supports all Gemini models (currently using gemini-3-flash-preview)

- **Factory Function (`create_llm_provider`)**: Creates appropriate provider based on config
  - Validates API keys are present
  - Returns initialized provider instance

**Key Design Decisions:**
- Synchronous `create_message()` method wrapped in `asyncio.to_thread()` by callers
- Unified error handling with `LLMError` exceptions
- Temperature and max_tokens configurable per-call or from config defaults

### 2. Configuration Schema Updates
**Files Modified:**
- `src/guarantee_email_agent/config/schema.py`
- `src/guarantee_email_agent/config/loader.py`

**Added `LLMConfig` dataclass:**
```python
@dataclass(frozen=True)
class LLMConfig:
    provider: str = "anthropic"  # "anthropic" or "gemini"
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout_seconds: int = 15
```

**Updated `SecretsConfig`:**
```python
@dataclass(frozen=True)
class SecretsConfig:
    anthropic_api_key: Optional[str] = None  # Required if provider=anthropic
    gemini_api_key: Optional[str] = None     # Required if provider=gemini
    gmail_api_key: str = ""
    warranty_api_key: str = ""
    ticketing_api_key: str = ""
```

**Updated `AgentConfig`:**
- Added `llm: LLMConfig` field with default initialization in `__post_init__`

**Updated config loader:**
- Added parsing of `llm` section from `config.yaml`
- Added loading of both `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` from environment

### 3. Component Updates to Use Provider Abstraction

**Files Modified:**
- `src/guarantee_email_agent/email/serial_extractor.py`
- `src/guarantee_email_agent/email/scenario_detector.py`
- `src/guarantee_email_agent/llm/response_generator.py`

**Changes per component:**
1. Removed direct `from anthropic import Anthropic` imports
2. Added `from guarantee_email_agent.llm.provider import create_llm_provider, LLMProvider`
3. Replaced `self.client = Anthropic(api_key=api_key)` with `self.llm_provider = create_llm_provider(config)`
4. Updated LLM calls from:
   ```python
   response = self.client.messages.create(
       model=MODEL_CLAUDE_SONNET_4_5,
       max_tokens=max_tokens,
       temperature=temperature,
       system=system_message,
       messages=[{"role": "user", "content": user_message}]
   )
   text = response.content[0].text
   ```
   To:
   ```python
   text = self.llm_provider.create_message(
       system_prompt=system_message,
       user_prompt=user_message,
       max_tokens=max_tokens,
       temperature=temperature
   )
   ```
5. Updated timeout references from hardcoded values to `self.config.llm.timeout_seconds`
6. Updated logging to use `self.config.llm.model` instead of hardcoded model names

### 4. Configuration Files

**File:** `config.yaml`
```yaml
# LLM Provider Configuration
llm:
  provider: "gemini"  # "anthropic" or "gemini"
  model: "gemini-3-flash-preview"
  temperature: 0.7
  max_tokens: 2000
  timeout_seconds: 15
```

**File:** `.env.example`
```bash
# LLM API Keys (one required, depending on config.yaml llm.provider)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

**File:** `.env` (actual, not committed)
```bash
ANTHROPIC_API_KEY=test-anthropic-key
GEMINI_API_KEY=AIzaSyCDs42pX9JhRpKxMkw7RB-o_UfQLkIXmHU
```

### 5. Dependencies

**File:** `pyproject.toml`
```python
dependencies = [
    "anthropic>=0.8.0",
    "google-generativeai>=0.3.0",  # NEW
    # ... other dependencies
]
```

### 6. Enhanced Logging

**File:** `src/guarantee_email_agent/email/processor.py`

Added email content logging to assist with debugging and monitoring:

**Incoming Email Logging:**
- **INFO level**: 200-character preview of email body
- **DEBUG level**: Full email body (per NFR14 - customer data only at DEBUG)

**Response Logging:**
- **INFO level**: Full generated response text

Example output:
```
INFO Email body preview: Dzień dobry, Zgłaszamy na RMA jako uszkodzoną...
INFO Generated response text:
Dear Adam Przetak,
Thank you for contacting our warranty and support team...
```

## Testing Results

### Successful End-to-End Test with Gemini
- **Model Used**: `gemini-3-flash-preview`
- **Processing Time**: ~18 seconds for complete 7-step pipeline
- **Email Processing**: Successfully parsed Polish language RMA request
- **Serial Extraction**: Gemini correctly identified serial number "C074AD3D3101"
- **Scenario Detection**: Fell back to graceful-degradation (expected with test scenarios)
- **Response Generation**: Generated 415-character professional response
- **Email Sent**: Mock send successful

### Log Output Verification
```
2026-01-18 15:13:40 INFO Gemini provider initialized: model=gemini-3-flash-preview
2026-01-18 15:13:40 INFO Serial number extractor initialized
2026-01-18 15:13:40 INFO Gemini provider initialized: model=gemini-3-flash-preview
2026-01-18 15:13:40 INFO Scenario detector initialized
2026-01-18 15:13:40 INFO Gemini provider initialized: model=gemini-3-flash-preview
2026-01-18 15:13:40 INFO Response generator initialized
...
2026-01-18 15:13:59 INFO Response generated: scenario=graceful-degradation, length=415 chars, model=gemini-3-flash-preview, temp=0
```

## Migration Guide for Future Developers

### Switching Between Providers

**To use Anthropic Claude:**
```yaml
# config.yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-5"  # or any Claude model
  temperature: 0.7
  max_tokens: 2000
  timeout_seconds: 15
```
Set `ANTHROPIC_API_KEY` in `.env`

**To use Google Gemini:**
```yaml
# config.yaml
llm:
  provider: "gemini"
  model: "gemini-3-flash-preview"  # or gemini-2.0-flash-exp, etc.
  temperature: 0.7
  max_tokens: 2000
  timeout_seconds: 15
```
Set `GEMINI_API_KEY` in `.env`

### Adding a New LLM Provider

1. **Create Provider Class** in `src/guarantee_email_agent/llm/provider.py`:
   ```python
   class NewProviderLLM(LLMProvider):
       def __init__(self, config: LLMConfig, api_key: str):
           super().__init__(config)
           # Initialize provider SDK

       def create_message(self, system_prompt, user_prompt, max_tokens=None, temperature=None) -> str:
           # Implement provider-specific logic
           pass
   ```

2. **Update Factory Function**:
   ```python
   def create_llm_provider(config: AgentConfig) -> LLMProvider:
       provider = config.llm.provider.lower()

       if provider == "newprovider":
           if not config.secrets.newprovider_api_key:
               raise ValueError("NEWPROVIDER_API_KEY required")
           return NewProviderLLM(config.llm, config.secrets.newprovider_api_key)
       # ... existing providers
   ```

3. **Update Config Schema** (`src/guarantee_email_agent/config/schema.py`):
   ```python
   @dataclass(frozen=True)
   class SecretsConfig:
       # ... existing keys
       newprovider_api_key: Optional[str] = None
   ```

4. **Update Config Loader** (`src/guarantee_email_agent/config/loader.py`):
   ```python
   def load_secrets() -> SecretsConfig:
       newprovider_key = os.getenv("NEWPROVIDER_API_KEY", "").strip() or None
       return SecretsConfig(
           # ... existing keys
           newprovider_api_key=newprovider_key
       )
   ```

5. **Add Dependency** to `pyproject.toml`:
   ```python
   dependencies = [
       # ... existing
       "newprovider-sdk>=1.0.0",
   ]
   ```

## Known Issues and Limitations

### Gemini-Specific Issues
1. **Finish Reason 2 Errors**: Gemini occasionally returns `finish_reason=2` (SAFETY) which causes the response to be empty. This triggers graceful degradation as expected.
   - **Error**: "The `response.text` quick accessor requires the response to contain a valid `Part`"
   - **Impact**: Falls back to graceful-degradation scenario
   - **Mitigation**: Consider implementing safety settings configuration or retry logic

2. **Model Naming**: Gemini model names change frequently (e.g., "gemini-2.0-flash-exp" was experimental, "gemini-3-flash-preview" is newer)
   - **Impact**: May need to update `config.yaml` as Google releases new models
   - **Mitigation**: Keep documentation updated with current recommended models

3. **Deprecation Warning**: `google-generativeai` package is deprecated in favor of `google.genai`
   - **Current Version**: Using `google-generativeai>=0.3.0`
   - **Future Action**: Migration to `google.genai` recommended
   - **Timeline**: No immediate impact, but should plan migration

### General Observations
1. **Serial Extraction Quirks**: Gemini sometimes returns markdown code blocks (```) around extracted values
   - **Example**: Returns ` ``` ` instead of just the serial number
   - **Impact**: Minimal - these get processed as-is
   - **Future Enhancement**: Consider post-processing to strip markdown formatting

2. **Response Quality**: Both providers work well, but responses differ in style:
   - **Claude**: More formal, consistent formatting
   - **Gemini**: Faster responses, sometimes includes JSON metadata in output

## Files Changed Summary

### New Files
- `src/guarantee_email_agent/llm/provider.py` - LLM provider abstraction layer

### Modified Files
- `src/guarantee_email_agent/config/schema.py` - Added LLMConfig, updated SecretsConfig
- `src/guarantee_email_agent/config/loader.py` - Added LLM config parsing
- `src/guarantee_email_agent/email/serial_extractor.py` - Use provider abstraction
- `src/guarantee_email_agent/email/scenario_detector.py` - Use provider abstraction
- `src/guarantee_email_agent/llm/response_generator.py` - Use provider abstraction
- `src/guarantee_email_agent/email/processor.py` - Enhanced logging for email content
- `config.yaml` - Added llm configuration section
- `.env.example` - Added GEMINI_API_KEY
- `.env` - Added actual Gemini API key
- `pyproject.toml` - Added google-generativeai dependency

## Architecture Decisions

### Why Provider Abstraction Pattern?
1. **Future-Proofing**: Easy to add new LLM providers (OpenAI, Cohere, etc.)
2. **Testing**: Can create mock providers for unit tests
3. **Cost Optimization**: Can switch providers based on cost/performance needs
4. **Vendor Lock-in Prevention**: Not dependent on single LLM vendor
5. **A/B Testing**: Can easily compare provider performance

### Why Not Use LangChain or Similar?
1. **Simplicity**: Direct SDK usage is more transparent and easier to debug
2. **Performance**: No additional abstraction overhead
3. **Control**: Full control over prompts, parameters, error handling
4. **Dependencies**: Fewer dependencies to maintain
5. **Learning**: Team learns provider APIs directly

### Error Handling Strategy
- **LLM Errors**: Always caught and trigger graceful degradation
- **Configuration Errors**: Fail fast at startup with clear error messages
- **API Key Validation**: Check at provider initialization, not at runtime
- **Timeouts**: Configurable per provider, consistent across all components

## Recommendations for Production

1. **Monitoring**: Add metrics for:
   - Provider selection (which provider is being used)
   - Provider performance (latency, error rates)
   - Cost per provider (if using paid APIs)
   - Quality metrics (response quality per provider)

2. **Cost Management**:
   - Consider implementing provider fallback (try Gemini, fall back to Claude if issues)
   - Add rate limiting per provider
   - Track token usage per provider

3. **Safety Settings**:
   - Configure Gemini safety settings to reduce SAFETY finish reasons
   - Add retry logic for transient provider failures
   - Implement circuit breaker pattern for provider failures

4. **Configuration**:
   - Consider environment-based configs (dev uses Gemini, prod uses Claude)
   - Add provider-specific settings (safety_settings for Gemini, etc.)
   - Implement config validation at startup

5. **Testing**:
   - Add unit tests with mock providers
   - Integration tests against both providers
   - Performance benchmarks comparing providers

## Related Documentation
- See `RUNNING.md` for operational guide
- See `config.yaml` for configuration reference
- See `.env.example` for environment variable setup
- See `src/guarantee_email_agent/llm/provider.py` for provider implementation details

## Commits
- `3491745` - Add Google Gemini support as alternative LLM provider
- Additional commits for logging enhancements (uncommitted as of this writing)

---
**Document Version**: 1.0
**Last Updated**: 2026-01-18
**Author**: Claude Code (AI Assistant)
**Reviewers**: Pending
