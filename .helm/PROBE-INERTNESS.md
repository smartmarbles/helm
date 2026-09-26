# Probe: `.helm/` Inertness Check

This file is an inertness probe. It exists solely to be checked for *absence* from every host's own diagnostics/context surface — VS Code's chat customization diagnostics view, Claude Code's `/context` → Memory files, Devin Desktop's Open customizations surface, and Cursor's rules/context surface. If any host surfaces this file's content, `.helm/` is not inert and a fallback pointer format applies instead.
