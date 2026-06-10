# Requirements Gate

Before any implementation, you must validate the task requirements.

## Main rule

Do not start coding until the requirements are clear, complete, consistent, and testable.

If requirements are incomplete, ambiguous, contradictory, or missing important input data, stop and ask questions first.

## Required analysis before implementation

For every task, check:

1. Goal  
What business or product problem should be solved?

2. Scope  
What exactly must be changed, added, removed, or kept unchanged?

3. Input data  
What files, modules, APIs, entities, configs, tests, logs, screenshots, or user flows are relevant?

4. Constraints  
What must not be touched?

5. Acceptance criteria  
How will we know the task is done correctly?

6. Edge cases  
What non-happy-path scenarios must be handled?

7. Dependencies  
What existing logic, models, services, routers, schemas, tests, migrations, or integrations can be affected?

8. Risks  
What can break if the task is implemented incorrectly?

9. Test coverage  
What tests must be added or updated?

10. Documentation  
What documentation must be updated after the change?

## Required output before coding

Before writing code, produce:

```text
REQUIREMENTS VALIDATION

Goal:
...

Scope:
...

Input data considered:
...

Confirmed constraints:
...

Missing information:
...

Contradictions:
...

Assumptions:
...

Acceptance criteria:
...

Edge cases:
...

Affected files/modules:
...

Required tests:
...

Documentation updates:
...

Decision:
- READY FOR IMPLEMENTATION
or
- NOT READY: QUESTIONS REQUIRED