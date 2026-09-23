"""Keep test-spawned Python subprocesses from writing ``__pycache__``.

``npm test`` runs the parent interpreter with ``-B``, but several tests spawn
``sys.executable -m evals...`` without it. Those children would otherwise create
``evals/__pycache__`` and make the subsequent ``npm run verify`` package-hygiene
check fail. Importing this module sets ``PYTHONDONTWRITEBYTECODE`` in the
environment, which every child process inherits.
"""

import os

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
