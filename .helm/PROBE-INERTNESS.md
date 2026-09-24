# Probe: `.helm/` Inertness Check

This file is a V-7 inertness probe (spec018, FR-046). It exists solely to be checked for *absence* from every host's own diagnostics/context surface — VS Code's chat customization diagnostics view, Claude Code's `/context` → Memory files, Devin Desktop's Open customizations surface, and Cursor's rules/context surface. If any host surfaces this file's content, `.helm/` is not inert and V-7's fallback applies.
