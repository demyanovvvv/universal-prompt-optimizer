---
description: Inspect or change Prompt Optimizer for the current OpenCode session.
---
Use the Prompt Optimizer server plugin state for this session. Interpret the
argument as one of the following commands:

- `status`: report mode, scope, quality gate, detected model/profile, task type,
  configuration validity and privacy-safe aggregate session counters.
- `explain`: report the latest decision, profile confidence, quality gate and
  preserve/add/skip reasons without revealing hidden reasoning or secrets.
- `on` or `auto`: enable AUTO for this session only.
- `off`: disable automatic optimization for this session only.
- `preview`: enable PREVIEW for this session only.
- `first` or `all`: change session scope.
- `pass`, `light`, `full` or `adaptive`: change the session quality gate.
- `reset`: remove session overrides and return to persistent configuration.

Do not edit configuration files unless the user explicitly requests a
persistent change. User instructions and host permissions remain higher
priority than this command.

$ARGUMENTS
