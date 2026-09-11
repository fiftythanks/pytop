## About

An experimental Linux system monitor written from scratch in Python for educational purposes, inspired by the layout and UI of [btop](https://github.com/aristocratos/btop).

### Goals
* **Learning:** Practical exercise in Python system-level programming, `/proc` filesystem parsing, and TUI rendering.
* **Zero C++ Dependencies:** Built entirely from scratch using pure Python to understand the underlying OS metric collection mechanics.

### Technical Debt
* The initial unit tests for `get_processes()` were written using a “God Fixture” that generated 27 processes statically, for most of the edge cases. While it is all right for a small project, if it ever grows larger, that fixture should probably be refactored. I decided to leave it as is because the tests worked well anyway, and the time could be used more wisely. But for any future test cases, the fixture returns a `generate_process()` function that allows creating processes individually for each unit test.
