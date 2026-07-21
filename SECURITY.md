# Security Policy

## Supported Versions

Security fixes are applied to the latest released version.

## Reporting A Vulnerability

Please use GitHub's private vulnerability reporting for this repository. If that feature is unavailable, contact the maintainer privately rather than opening a public issue. Include reproduction steps, impact, affected files or versions, and any suggested mitigation. Allow reasonable time for triage before public disclosure.

Do not include provider keys, credentials, or sensitive raw run artifacts in a report.

## Execution Warning

This benchmark executes model-generated Clojure and permits a coding agent to edit a temporary workspace. OpenCode tool permissions are a practical workflow boundary, **not an operating-system sandbox**. Temporary directories, loopback binding, and command restrictions do not protect the host from a malicious model, compromised provider, vulnerable dependency, or harness escape.

Run the benchmark only with models and providers you trust. Use an appropriately isolated machine, container, or virtual machine when evaluating untrusted output. Keep credentials scoped and avoid exposing sensitive files or network services to the benchmark process.
