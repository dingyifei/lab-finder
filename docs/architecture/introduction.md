# Introduction

This document outlines the overall project architecture for Lab Finder, including backend systems, shared services, and non-UI specific concerns. Its primary goal is to serve as the guiding architectural blueprint for AI-driven development, ensuring consistency and adherence to chosen patterns and technologies.

**Relationship to Frontend Architecture:**
This is a CLI-only tool with no graphical user interface. All user interaction occurs through command-line prompts and markdown report outputs.

## Starter Template or Existing Project

**Decision:** Build from scratch without a starter template.

**Rationale:** This is a greenfield Python project built on the Claude Agent SDK. No standard starter templates match the specific multi-agent orchestration architecture required. The Claude Agent SDK provides the core framework, and we'll structure the project to precisely fit the multi-agent orchestration needs.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-06 | 0.1 | Initial architecture draft | Winston (architect) |
| 2025-10-06 | 0.2 | SDK validation updates: Added AgentDefinition implementations, web scraping decision tree, implementation patterns, and risk assessment | Winston (architect) |
| 2025-10-06 | 0.3 | Parallel execution optimization: Split Epic 5 into 5A/5B for concurrent execution with Epic 4, added convergence validation pattern, updated mermaid diagram | Sarah (PO) |
