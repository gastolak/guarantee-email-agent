"""Debug script to test LLM responses."""
import asyncio
import sys
import time

sys.path.insert(0, 'src')

from guarantee_email_agent.config import load_config
from guarantee_email_agent.llm.provider import create_llm_provider


async def test_llm():
    """Test a simple LLM call."""
    print("Loading config...")
    config = load_config("config.yaml")

    print(f"Provider: {config.llm.provider}")
    print(f"Model: {config.llm.model}")
    print(f"Timeout: {config.llm.timeout_seconds}s")
    print(f"Max tokens: {config.llm.max_tokens}")
    print()

    print("Creating LLM provider...")
    provider = create_llm_provider(config)

    print("Testing simple LLM call...")
    start = time.time()

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                provider.create_message,
                system_prompt="You are a helpful assistant.",
                user_prompt="Extract the serial number from this text: 'My device serial is SN12345'",
                max_tokens=100,
                temperature=0
            ),
            timeout=config.llm.timeout_seconds
        )

        elapsed = time.time() - start
        print(f"\n✓ Success in {elapsed:.2f}s")
        print(f"Response: {response}")

    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"\n✗ Timeout after {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n✗ Error after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_llm())
