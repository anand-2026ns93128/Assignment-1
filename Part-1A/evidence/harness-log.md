# Part 1A – Harness Log: Smart Todo CLI

## 1. Context

My Smart Todo app helps users create, organize, prioritize, update, and track
their daily tasks efficiently. It is designed for students, professionals, and
anyone who wants a simple and reliable way to manage daily activities and
improve productivity.

I selected the Todo problem because it is practical, easy to understand, and
represents a real-world application with clear functional requirements. It also
provides opportunities to implement CRUD operations, input validation, task
management, and automated testing. The Rate Limiter is more focused on
infrastructure and traffic management, whereas Todo allowed me to demonstrate a
complete application development workflow.

- Spec: Part-1A/specs/001-smart-todo-cli/spec.md (59 acceptance criteria, 19 functional requirements, 64 tasks)
- Coding agent: Claude Code
- Spec Kit steps: constitution and specify on 5 Nov; clarify, plan, tasks and analyze on 7 Nov; implement on 7 Nov

The most useful aspect of Spec Kit was its structured, specification-driven
development approach. Instead of immediately asking the coding agent to generate
code, I first defined the requirements, clarified the technical approach, and
established implementation tasks. I found it particularly useful that the
workflow separates specification, planning, task breakdown, and implementation.
This makes AI-assisted development more predictable, reduces misunderstandings,
and makes it easier to validate the final application against its original
requirements.

## 2. Initial generation

Before running /speckit-implement, I instructed the coding agent to implement all
tasks in tasks.md in the specified order and follow the test-first approach. I
explicitly told it not to run the harness, not to perform a final
lint/security/coverage cleanup, and never to modify, skip, or weaken tests or
gate settings. The reason was to preserve the coding agent's first
implementation without artificially improving its results to pass the quality
checks. I wanted the independent harness to evaluate the actual output
objectively. This ensures that the test results reflect genuine code quality
rather than changes made by the agent to satisfy the evaluator.

- Initial generation: commit tagged `1A-initial-generation`, snapshot in `evidence/initial-generation/src`

## 3. Harness gates

| Gate | Why it matters for Smart Todo |
|------|-------------------------------|
| Ruff | Identifies Python coding errors, unused imports, and style inconsistencies, keeping the code clean and maintainable. |
| Bandit | Checks for common security vulnerabilities, particularly important when handling user inputs and application data. |
| Pytest | Verifies that task creation, updating, deletion, listing, and validation work correctly. |
| Coverage ≥ 90% | Ensures that most application logic is tested, reducing the risk of bugs in task-management functionality. |
| Python 3.11 | Ensures compatibility with the specified runtime and consistent application behaviour across development and execution environments. |

## 4. Run history

| # | Run (UTC) | Python | Ruff | Bandit (med/high · low) | Pytest (tests) | Coverage | Python check | Overall |
|---|---|---|---|---|---|---|---|---|
| 1 | 20261107T161924Z | 3.13.2 | PASS | PASS (0 · 28) | PASS (10) | FAIL (report missing) | WARN | FAIL |
| 2 | 20261107T162113Z | 3.13.2 | FAIL | PASS (0 · 61) | PASS (39) | PASS 92.39% | WARN | FAIL |
| 3 | 20261107T162144Z | 3.13.2 | PASS | PASS (0 · 61) | PASS (39) | PASS 92.39% | WARN | PASS |
| 4 | 20261107T163332Z | 3.13.2 | PASS | PASS (0 · 102) | PASS (87) | PASS 95.15% | WARN | PASS |
| 5 | 20261107T163622Z | 3.13.2 | PASS | PASS (0 · 146) | PASS (136) | PASS 97.51% | WARN | PASS |
| 6 | 20261107T163721Z | 3.13.2 | FAIL | PASS (0 · 154) | PASS (155) | PASS 98.00% | WARN | FAIL |
| 7 | 20261107T163741Z | 3.13.2 | PASS | PASS (0 · 154) | PASS (155) | PASS 98.00% | WARN | PASS |
| 8 | 20261107T163841Z | 3.13.2 | PASS | PASS (0 · 178) | PASS (176) | PASS 98.77% | WARN | PASS |
| 9 | 20261107T163924Z | 3.13.2 | PASS | PASS (0 · 188) | PASS (184) | PASS 98.78% | WARN | PASS |
| 10 | 20261107T164012Z | 3.13.2 | PASS | PASS (0 · 200) | PASS (190) | PASS 98.78% | WARN | PASS |
| 11 | 20261107T164124Z (final) | 3.13.2 | PASS | PASS (0 · 209) | PASS (198) | PASS 98.78% | FAIL | FAIL |
| 12 | 20261107T171956Z (final) | 3.11.9 | PASS | PASS (0 · 209) | PASS (198) | PASS 98.78% | PASS | PASS |

## 5. Failure → repair cycles

### Cycle 1: Coverage failure
- Failing run: 20261107T161924Z
- Fixed in run: 20261107T162113Z

The coverage gate reported 0% because the application code had not yet been
implemented or imported, so no coverage data could be collected. After the
application code and its tests were created, coverage was measured successfully
and reached 92.39%.

### Cycle 2: Ruff errors in errors.py and test_core.py
- Failing run: 20261107T162113Z
- Fixed in run: 20261107T162144Z

Ruff reported two issues: an E501 line-length violation in
src/smart_todo/errors.py and a UP012 warning about an unnecessary UTF-8 encoding
argument in tests/unit/test_core.py. The coding agent corrected the line
formatting and removed the unnecessary argument.


### Cycle 3: Ruff error in models.py
- Failing run: 20261107T163721Z
- Fixed in run: 20261107T163741Z

Ruff reported another E501 line-length violation in src/smart_todo/models.py,
in the ALLOWED_TRANSITIONS definition. The coding agent reformatted the
definition across multiple lines while keeping the same three allowed
transitions.

### Cycle 4: Python version mismatch
- Failing run: 20261107T164124Z
- Fixed in run: 20261107T171956Z

The final harness run failed the Python version gate because the environment was
using Python 3.13.2 instead of the required Python 3.11; the other four gates
passed. Python 3.11 was not installed, so I installed Python 3.11.9 using
winget. All five gates then passed.


### Additional agent-reported fixes
Claude Code also reported fixing a Bandit finding related to xml.etree and two
test mistakes. These changes were mentioned in the agent's summary but were not
separately identified in the harness run history, so I am recording them as
agent-reported fixes rather than independently verified failure-and-repair
cycles. The final harness run nevertheless confirmed that Bandit passed with
zero medium/high findings and that all 198 tests passed.

## 6. Final automated result

Final run 20261107T171956Z (Python 3.11.9): ruff PASS · bandit PASS (0 medium/high,
209 low) · pytest PASS (198 tests, 0 failures) · coverage 98.78% (threshold 90%) ·
Python check PASS · **Overall PASS**


## 7. Human review and decision

**What I tested by hand:**
I manually reviewed the Smart Todo application to check its main user-facing
behaviour. I focused on whether the application behaved correctly.


**Did it behave as specified:**
The behaviour I reviewed appeared consistent with the specification. In
particular, the task status transitions follow the allowed rules:
todo → in_progress, in_progress → done, and todo → done. Invalid transitions
are rejected.

**Test I checked against its acceptance criterion:**
I checked test_AC27_done_to_todo_rejected against AC-27. The test starts with a
task in status done, runs "status 1 todo", and checks that the command fails
with exit code 1, prints nothing to normal output, shows the exact error message
"Error: cannot change status of task 1 from done to todo.", and leaves the data
file unchanged. This matched the acceptance criterion. The ALLOWED_TRANSITIONS
definition also remained unchanged when the Ruff formatting issue was corrected.

**Decision: ACCEPT, with limitations.**
The final automated harness run (20261107T171956Z) passed all five gates:
Python 3.11.9, Ruff, Bandit, pytest (198 tests), and 98.78% coverage. My review
of the specified status-transition behaviour was also consistent with FR-010. I
therefore accept the implementation for the scope of this assignment, not as a
claim that it is production-ready.

**Limitations and residual risks:**
The project has been checked against its defined requirements and automated
gates, but that does not prove that every real-world usage scenario has been
covered. The application may still have usability issues or edge cases that
were not exercised during testing. The reported Bandit and test corrections
should also be distinguished from individually recorded harness failures and
repairs.

**Before real users relied on it, I would add:**
Broader end-to-end and user-acceptance testing, tests for more edge cases and
invalid inputs, and a review of how the application handles errors and
unexpected data. I would also improve user documentation and carry out a
security and usability review.