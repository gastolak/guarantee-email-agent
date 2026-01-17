---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: []
date: 2026-01-17
author: mMaciek
---

# Product Brief: guarantee-email-agent

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

The Guarantee Email Agent is a tailor-made, instruction-driven AI system designed to fully automate warranty inquiry email processing. Unlike traditional hardcoded automation, the agent's behavior is defined entirely through editable instruction files—a main orchestration instruction set plus modular scenario-specific instructions that the LLM dynamically loads based on context. The agent autonomously handles the complete workflow: reading Gmail inbox via MCP, analyzing email content, extracting serial numbers, validating warranties through external API, routing to the appropriate scenario instructions, drafting contextually appropriate responses, and registering tickets in the external ticketing system when warranties are valid. Built with an evaluation framework that tests end-to-end scenarios against expected responses, the system enables continuous improvement through instruction refinement without code changes. This delivers 100% automation of warranty triage while maintaining flexibility, transparency, and quality assurance.

---

## Core Vision

### Problem Statement

Your company currently processes warranty inquiry emails through a manual, time-consuming workflow. Support staff must read each email, extract serial numbers, call the warranty API to check validity, draft appropriate responses, send emails back to customers, and create tickets in the external system for valid warranty cases. This repetitive triage work consumes valuable time and takes the team away from their core responsibility: actually solving customer problems. Additionally, traditional automation solutions lock behavior into rigid code, making it difficult to adapt to new scenarios or refine responses based on real-world feedback.

### Problem Impact

- **Time drain:** Manual processing of each warranty inquiry reduces team capacity for actual support work
- **Repetitive overhead:** Support staff spend time on predictable, automatable tasks rather than high-value problem-solving
- **Scalability constraint:** As warranty inquiry volume grows, manual processing doesn't scale efficiently
- **Delayed responses:** Manual workflows mean customers wait longer for basic warranty status information
- **Inflexible automation:** Traditional automation tools require code changes to adapt behavior, making continuous improvement slow and developer-dependent

### Why Existing Solutions Fall Short

Off-the-shelf email automation tools and workflow platforms are too generic for this specific use case. They require extensive configuration, struggle with the nuances of your specific warranty API integration and ticket system, and still don't deliver seamless end-to-end automation. Generic chatbots lack the intelligence to handle varied email formats and business logic. More critically, traditional automation systems embed logic in code—making it difficult for non-developers to refine behavior, add edge cases, or improve responses based on real-world performance. Your company needs a solution that's both precisely tailored to your systems AND easily adaptable through instruction refinement rather than code changes.

### Proposed Solution

The Guarantee Email Agent is a custom AI agent built on an instruction-driven architecture using LLM reasoning and MCP integrations. The system's intelligence and behavior are defined through editable instruction files rather than hardcoded logic:

**Core Workflow:**
1. Monitors and reads incoming emails from Gmail via MCP
2. Analyzes email content using LLM intelligence following main instruction set
3. Extracts serial numbers and calls external warranty API to validate status
4. Dynamically loads scenario-specific instruction files based on context (valid warranty, expired warranty, missing information, etc.)
5. Follows scenario instructions to draft contextually appropriate responses
6. Sends responses via Gmail MCP integration
7. Automatically registers support tickets in external ticketing system (via API) when warranties are valid

**Instruction Architecture:**
- **Main instruction file:** Core orchestration logic and scenario detection
- **Modular scenario instructions:** Separate instruction files for each workflow path (valid warranty, invalid warranty, edge cases)
- **Dynamic loading:** LLM intelligently routes to appropriate scenario instructions based on analysis
- **Version controlled:** All instructions tracked in git for transparency and evolution

**Quality Assurance:**
- **End-to-end evaluation framework:** Test suite with example warranty emails mapped to expected agent responses
- **Complete scenario coverage:** Evals validate the full workflow from email receipt through final action
- **Safe iteration:** Run evals before deploying instruction changes to catch regressions
- **Continuous improvement:** Refine instructions based on real-world performance with confidence

### Key Differentiators

- **Instruction-first architecture:** Agent behavior defined in easily editable files, not locked in code—enabling non-developers to refine and extend the system
- **Modular scenario design:** Scenario-specific instruction files provide clear separation and maintainability
- **LLM-powered intelligence:** Handles varied email formats, context understanding, and intelligent routing that rule-based systems can't match
- **Eval-driven quality:** Built-in testing framework ensures instruction changes maintain quality across all scenarios
- **Complete automation:** 100% autonomous handling of warranty triage from inbox to ticket creation
- **Continuous evolution:** Instructions can be enriched over time based on real-world feedback without code deployment cycles
- **Transparent and controllable:** Single source of truth for agent behavior, visible and auditable
- **Tailor-made integration:** Built specifically for your warranty API, ticket system, and business workflow

## Target Users

### Primary Users

**CTO - Technical Leader in Small Firm**

The primary user is a CTO in a small firm who is responsible for both technology decisions and operational efficiency. With limited resources and a lean team, this technical leader needs high-impact automation that delivers measurable reliability without requiring constant oversight.

**Role & Context:**
- Manages technology strategy and daily operations in a resource-constrained environment
- Accountable for team productivity and customer service quality
- Makes build-vs-buy decisions based on specific business needs
- Values solutions that can be refined and improved over time

**Current Challenges:**
- Team capacity consumed by repetitive warranty email triage work
- No mechanism to guarantee consistent quality and response times at scale
- Cannot justify hiring additional staff solely for email processing
- Needs confidence that automation won't create costly errors or customer dissatisfaction
- Traditional automation tools either too rigid or lack quality assurance mechanisms

**Success Criteria:**
- **99% correctness** in warranty email handling - the defining metric of success
- Automated processing of all warranty inquiries without human intervention for triage
- Team capacity redirected to high-value customer problem-solving work
- Visibility and confidence through evaluation framework that quality standards are maintained
- Ability to iteratively refine agent behavior through instruction updates as new edge cases emerge

**Why This Solution:**
- Instruction-driven architecture enables continuous improvement without code deployments
- Built-in eval framework provides the quality assurance needed to achieve 99% correctness target
- Tailor-made for specific warranty API and ticketing system integration needs
- Transparent, auditable logic through visible instruction files
- Technical control and flexibility without vendor lock-in

### Secondary Users

**Support Staff:**
Secondary beneficiaries who are freed from repetitive warranty email triage work, allowing them to focus exclusively on resolving actual warranty cases that the agent routes to them via ticket creation.

**Customers:**
Email senders who experience faster, more consistent responses to warranty inquiries without knowing they're interacting with an automated agent.

### User Journey

**CTO Journey - From Manual Process to Automated Confidence:**

1. **Problem Recognition:** CTO identifies that warranty email processing is consuming disproportionate team time with inconsistent quality
2. **Solution Design:** Decides to build tailor-made instruction-driven agent rather than configure generic automation tools
3. **Initial Setup:** Creates main instruction files and scenario-specific instructions for warranty workflows
4. **Eval Framework:** Builds test suite with example emails and expected responses to validate 99% correctness target
5. **Deployment:** Agent begins autonomous processing of warranty emails via MCP integrations
6. **Monitoring & Refinement:** Reviews eval results, identifies edge cases, refines instructions iteratively
7. **Success Realization:** Achieves 99% correctness, team capacity freed up, response times improved, quality assured

## Success Metrics

### Primary Success Metric

**99% Eval Pass Rate** - The definitive measure of system correctness. Success is achieved when the agent consistently passes 99% or more of the evaluation test suite, demonstrating reliable, accurate handling of warranty inquiry emails across all scenarios.

**Measurement Method:**
- Run complete eval suite against current instruction set
- Track pass rate: (passed scenarios / total scenarios) × 100
- Target: ≥99% pass rate before deployment and ongoing

**Continuous Improvement Feedback Loop:**
- When agent fails an eval scenario, add that case to the permanent test suite
- Refine main or scenario-specific instructions to handle the edge case
- Re-run full eval suite to verify fix doesn't break existing scenarios
- System becomes progressively more reliable and comprehensive over time

### Supporting Operational Metrics

**Quality Improvement Over Time:**
- **Eval suite growth:** Number of scenarios covered (expanding as new edge cases are discovered)
- **Pass rate trend:** Movement toward and maintenance of 99%+ correctness
- **Failure frequency:** Decreasing time between eval failures (increasing reliability)

**Operational Impact:**
- **Team time saved:** Hours per week freed from manual warranty email triage work
- **Response time:** Agent processing speed compared to manual workflow baseline
- **Zero-touch rate:** Percentage of warranty emails processed completely autonomously without human intervention

### Business Objectives

**Primary Business Value:**
- **Support team capacity optimization:** Redirect team effort from repetitive triage to high-value customer problem-solving
- **SLA compliance:** Consistent, reliable response times for warranty inquiries
- **Scalability:** Handle growing email volume without proportional headcount increases

**Strategic Success Indicators:**
- Agent autonomously processes 100% of warranty inquiry emails
- Support team focuses exclusively on resolving actual warranty cases (tickets created by agent)
- CTO has confidence through eval framework that quality standards are maintained
- System improves continuously through instruction refinement based on real-world performance

### Key Performance Indicators

1. **Correctness KPI:** ≥99% eval pass rate (measured continuously)
2. **Automation KPI:** 100% of warranty emails processed by agent without manual triage
3. **Efficiency KPI:** Team time savings measured in hours/week redirected from triage to problem-solving
4. **Quality KPI:** Eval suite comprehensiveness (number of scenarios covered, growing over time)
5. **Reliability KPI:** System uptime and successful processing rate of incoming emails

## MVP Scope

### Core Features

**1. Gmail Integration via MCP**
- Monitor incoming warranty inquiry emails from designated inbox
- Parse email content, metadata, and context
- Send automated responses back to customers via Gmail API

**2. LLM-Powered Email Analysis**
- Analyze email content to understand inquiry type and context
- Extract serial numbers from varied email formats
- Detect warranty inquiry scenarios and route to appropriate instruction set

**3. Instruction-Driven Workflow Architecture**
- **Main instruction file:** Core orchestration logic and scenario detection
- **Scenario-specific instruction files:** Modular instructions for each workflow path
  - Valid warranty scenario
  - Invalid/expired warranty scenario
  - Missing information scenario
  - Edge case scenarios
- **Dynamic instruction loading:** LLM intelligently routes to appropriate scenario instructions based on analysis
- **Version-controlled instructions:** All instruction files tracked in git for transparency and evolution

**4. Warranty Validation via MCP**
- Integrate with external warranty API via MCP
- Query warranty status using extracted serial numbers
- Handle API responses and error conditions

**5. Contextual Response Generation**
- Draft appropriate email responses based on warranty validation results
- Follow scenario-specific instruction guidance for tone, content, and next steps
- Maintain consistency and quality across all responses

**6. Ticket System Integration via MCP**
- Automatically create support tickets in external ticketing system via MCP API
- Populate ticket with relevant information (serial number, warranty status, customer details)
- Trigger only for valid warranty cases requiring support team action

**7. Evaluation Framework**
- **Test suite:** Collection of example warranty emails with expected agent responses
- **End-to-end validation:** Run complete workflow scenarios through eval suite
- **Pass rate tracking:** Measure correctness against 99% target
- **Continuous improvement loop:**
  - Failed evals added to permanent test suite
  - Instructions refined to handle edge cases
  - Re-run evals to verify fixes without breaking existing scenarios

### Out of Scope for MVP

The following features are intentionally deferred to maintain focus on core automation workflow:

- **Email attachments processing:** Initial version handles text-based emails only
- **Multi-language support:** MVP operates in single language (English)
- **Reporting dashboard:** No built-in analytics UI; success tracked via eval pass rate
- **Manual review/approval mode:** MVP is fully autonomous; no human-in-the-loop option
- **Multiple product lines:** MVP handles single warranty API; multi-product support deferred
- **Advanced NLP features:** No sentiment analysis, urgency detection, or categorization beyond warranty validation
- **Integration with additional systems:** CRM, knowledge base, or other business systems not included in MVP
- **Email thread continuation:** MVP handles initial inquiry only; follow-up conversations out of scope

### MVP Success Criteria

**Primary Success Gate:**
- Achieve **≥99% eval pass rate** demonstrating reliable, accurate warranty email processing across all test scenarios

**Operational Validation:**
- Successfully process 100% of warranty inquiry emails without manual intervention
- Zero critical failures (incorrect warranty status, failed API calls, unsent responses)
- Instruction refinement cycle functional (failed evals → instruction updates → re-validation)

**Business Validation:**
- Measurable team time savings from eliminated manual triage work
- Support team capacity redirected to actual warranty case resolution
- CTO confidence in system reliability through transparent eval results

**Technical Validation:**
- All MCP integrations (Gmail, warranty API, ticketing system) functioning reliably
- Instruction-driven architecture supports iterative improvement
- Eval framework provides comprehensive scenario coverage

### Future Vision

**Post-MVP Enhancements (V2.0+):**

**Expanded Intelligence:**
- Multi-language email support for international customers
- Email attachment processing (warranty documentation, receipts, photos)
- Sentiment analysis and urgency detection for prioritization
- Advanced categorization beyond warranty validation

**Enhanced Automation:**
- Email thread continuation and follow-up handling
- Proactive notification system for warranty expiration
- Automated escalation for complex cases
- Integration with knowledge base for FAQ responses

**Enterprise Capabilities:**
- Multi-product line support with different warranty APIs
- Reporting dashboard with analytics and insights
- Manual review mode for quality assurance workflows
- A/B testing framework for instruction optimization
- Integration with CRM, billing, and other business systems

**Scale & Optimization:**
- Support for multiple email inboxes/departments
- Load balancing and performance optimization for high volume
- Advanced eval suite with synthetic scenario generation
- Continuous learning from production data (with privacy safeguards)

**Long-term Vision:**
- Platform approach: generalize instruction-driven architecture for other support workflows
- Marketplace for scenario instruction templates
- AI-assisted instruction refinement based on eval patterns
- Predictive warranty issue detection before customers reach out
