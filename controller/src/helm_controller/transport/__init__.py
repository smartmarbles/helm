"""Copilot-specific transport layer for the Helm controller.

This subpackage holds the only host-specific code in the controller: the
localhost HTTP server that Python hook wrappers call. Core enforcement stays
host-neutral and never imports from here.
"""
