"""Module entry point so ``python -m helm_controller`` launches the controller.

Used by the ``launch-helm-controller`` VS Code task (``.vscode/tasks.json``),
which runs ``${command:python.interpreterPath} -m helm_controller --workspace
${workspaceFolder}`` on folder open.
"""

from __future__ import annotations

from helm_controller.server import main

if __name__ == "__main__":
    raise SystemExit(main())
