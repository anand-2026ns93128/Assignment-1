\# Part 1A – Harness Log: Smart Todo CLI



\## 1. Context

<!--

* This App is for Smart Todo CLI on Python 3.11 and standard library only.
* Spec path = Part-1A/specs/001-smart-todo-cli/spec.md, which grew from 54 to 59 ACs after analyze with 19 FRs
* 64 taske used and gent used is Claude Code
* Dates: 

&#x09;Constitution and spec: 5 Nov

&#x09;Clarify, plan, tasks and analyze: 7 Nov, early morning

&#x09;Implementation: 7 Nov, afternoon

* Clarify asked no questions. It left two low-impact items for the plan.
* Analyze found CRITICAL, HIGH and MEDIUM issues (C1–C3, I1, among others), and you had all 10 fixed. I1 changed the spec, with a dated note. -->



\## 2. Initial generation

<!-- 

* Tag 1A-initial-generation on branch 001-smart-todo-cli.
* Your instruction to the agent: don’t run the final harness, and never weaken tests.
* The task list still required harness runs at each phase checkpoint, so runs happened during implementation. -->



\## 3. Harness gates

<!-- 

* The five gates: ruff, bandit (0 medium/high), pytest, coverage at least 90%, and Python 3.11 -->



\## 4. Run history

<!-- 

* Mode                 LastWriteTime         Length Name
* \----                 -------------         ------ ----
* d-----         11/7/2026   6:35 PM                20261107T1619
* &#x20;                                                 24Z
* d-----         11/7/2026   6:35 PM                20261107T1621
* &#x20;                                                 13Z
* d-----         11/7/2026   6:35 PM                20261107T1621
* &#x20;                                                 44Z
* d-----         11/7/2026   6:35 PM                20261107T1633
* &#x20;                                                 32Z
* d-----         11/7/2026   6:35 PM                20261107T1636
* &#x20;                                                 22Z
* d-----         11/7/2026   6:35 PM                20261107T1637
* &#x20;                                                 21Z
* d-----         11/7/2026   6:35 PM                20261107T1637
* &#x20;                                                 41Z
* d-----         11/7/2026   6:35 PM                20261107T1638
* &#x20;                                                 41Z
* d-----         11/7/2026   6:35 PM                20261107T1639
* &#x20;                                                 24Z
* d-----         11/7/2026   6:35 PM                20261107T1640
* &#x20;                                                 12Z
* d-----         11/7/2026   6:35 PM                20261107T1641
* &#x20;                                                 24Z
* d-----         11/7/2026   6:35 PM                20261107T1719
* &#x20;                                                 56Z -->



\## 5. Failure → repair cycles

<!--

* Ruff: long lines, fixed by shortening the lines. The rule wasn’t disabled.
* Bandit: xml.etree parsing of JUnit output was flagged MEDIUM. The parsing was switched to a regex.
* Tests: the AC-21 test’s monkeypatch.undo() also undid the directory change, and an equal-priority ordering test expected the wrong order. Both were judged to be test errors and corrected. Verify this yourself in the diff.
* Python: the --final run failed because 3.13.2 was installed. You installed 3.11.9 with winget and reran, and run 20261107T171956Z passed every gate. -->



&#x20;     

\## 6. Final automated result

<!-- 

* Ruff PASS
* Bandit PASS (0 medium/high, 209 LOW)
* 198 tests, 0 failures
* Coverage 98.78%
* Python 3.11.9
* Overall PASS -->



\## 7. Human review and decision

<!--

* The harness only checks what someone thought to test. A 100% pass means “the code does what the tests check”. It doesn’t mean the code is correct for every real use. A human reviewer looks for the gap between the two, then takes responsibility for the decision.
* Using the app by hand. Automated tests use exact, planned inputs. A person tries things the way a real user would and notices things tests can’t judge: whether error messages are clear, whether the output is easy to read, whether a command feels natural.
* Spot-checking the tests. A test called test\_AC05\_… could, in theory, check something weaker than AC-05 says. Opening a few and comparing them to the spec tells you whether the passing tests can be trusted. That matters most for the tests the agent changed during implementation.
* Common limitations and risks for an app like this:

  * Concurrency. If two terminals run the app at the same moment, both may read the file, change it and save. The second save overwrites the first, and a task is lost. Atomic writes stop a half-written file, but they don’t stop this. Your spec deliberately excluded concurrency
  * Scale. The whole JSON file is read and rewritten on every command. That’s fine for hundreds of tasks, but it gets slower with very large lists.
  * Platform. The harness ran only on your Windows machine with Python 3.11. Behaviour on Mac or Linux, for example line endings or file renaming, hasn’t been verified by a run.
  * The 209 LOW bandit findings. Most are bandit rule B101, which flags every assert statement. Python can skip asserts when run in optimised mode, so bandit warns about them. In test files, asserts are the normal way to write tests, so reviewers usually accept them there. The question to ask yourself is whether any of the 209 are in src/ rather than tests/.
  * Data safety. The app works on one local file, with no backup or undo. If the file is deleted or corrupted by something outside the app, the data is gone. The app detects corruption, but it can’t recover from it. -->

