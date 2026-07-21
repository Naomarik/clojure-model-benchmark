# Third-Party Software And Models

## Model Weights And Services

This repository does not distribute model weights, GGUF files, provider credentials, or hosted inference services. Model names in configuration, documentation, and results identify external systems used in experiments; they do not imply ownership, endorsement, redistribution rights, or a license grant. Obtain model weights and service access from their respective publishers and follow their licenses and acceptable-use terms.

## External Tools

The harness interoperates with external projects that are installed separately:

- [OpenCode](https://opencode.ai/) supplies agent orchestration and provider routing.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) can serve local GGUF models through an OpenAI-compatible API.
- [Babashka](https://babashka.org/) executes Clojure fixtures, graders, and socket REPLs.

Those projects remain governed by their own licenses. They are not vendored or relicensed by this repository. Generated `.opencode` package files and `node_modules` are local tooling artifacts and are not part of the source release.

## Project Content

Unless a file says otherwise, the benchmark harness, prompts, graders, reference solutions, and fixtures in this repository are project-owned and released under the MIT License. A fixture that incorporates third-party material must carry clear provenance and compatible licensing before acceptance.
