---
description: Diagnoses and repairs one isolated Clojure fixture through its prestarted REPL.
mode: primary
temperature: 0
permission:
  "*": deny
  read: allow
  edit: allow
  glob: allow
  grep: allow
  list: allow
  bash:
    "*": deny
    "./repl-eval *": allow
  external_directory:
    "*": deny
---

Work only in the provided fixture directory. Use read, glob, grep, and list rather than shell commands to inspect files. Diagnose the observed behavior with the prestarted REPL before editing. Edit only `src/**`. Use `./repl-eval 'FORM'` for live evaluation, then reload affected namespaces and verify the repaired behavior in the same REPL. Do not use external network access or inspect paths outside the fixture. Finish with a concise summary of the diagnosis and verification.
