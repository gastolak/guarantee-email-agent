"""Quick test of step-based workflow."""
import asyncio
import sys
sys.path.insert(0, 'src')

from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.email import create_email_processor

async def test_step_workflow():
    """Test step-based workflow with sample email."""
    # Load config
    config = load_config("config.yaml")
    print(f"✓ Config loaded: use_step_orchestrator={config.agent.use_step_orchestrator}")

    # Create processor
    processor = create_email_processor(config)
    print(f"✓ Processor created")
    print(f"  - Step orchestrator: {processor.step_orchestrator}")
    print(f"  - Max steps: {processor.step_orchestrator.max_steps}")

    # Create sample email
    sample_email = {
        "id": "test-001",
        "threadId": "thread-001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Device warranty check"},
                {"name": "From", "value": "customer@example.com"},
                {"name": "To", "value": "support@acnet.com"}
            ],
            "body": {
                "data": "SGVsbG8sIG15IGRldmljZSB3aXRoIHNlcmlhbCBDMDc0QUQzRDMxMDIgaXMgbm90IHdvcmtpbmcuIENhbiB5b3UgY2hlY2sgdGhlIHdhcnJhbnR5Pw=="
                # Base64: "Hello, my device with serial C074AD3D3102 is not working. Can you check the warranty?"
            }
        },
        "internalDate": "1738492800000"
    }

    print(f"\n✓ Testing step-based workflow...")
    print(f"  Email ID: {sample_email['id']}")

    try:
        # This should route to process_email_with_steps due to config flag
        result = await processor.process_email_with_functions(sample_email)

        print(f"\n✓ Processing complete!")
        print(f"  Success: {result.success}")
        print(f"  Scenario: {result.scenario_used}")
        print(f"  Serial: {result.serial_number}")
        print(f"  Email sent: {result.response_sent}")
        print(f"  Processing time: {result.processing_time_ms}ms")

        if result.error_message:
            print(f"  Error: {result.error_message}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_step_workflow())
