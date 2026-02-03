---
name: 'eval-check'
description: 'check eval definition'
---
run eval, "uv run python -m guarantee_email_agent.cli eval --scenario <<scenario>> --verbose"

look read eval definition. check whether the eval definition 
is correct given current implementation and message templates from @instructions/ or is there any problem with code.
