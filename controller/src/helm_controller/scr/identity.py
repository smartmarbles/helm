"""Single-source identity generation for SCR records (spec015 Task 2.4).

The SCR (Scoped Context Record) subsystem addresses every persisted record by a
``record_id`` primary key. ``record_id`` is a distinct identifier class from the
runtime-store ``workflow_id`` (see :mod:`helm_controller.store.identity`), the
lock ``token``, and the ``operation_id`` content hash — it is the persisted
primary key of the SCR tier.

This module is the ONLY ``record_id`` generation path in the codebase: both the
write-queue auto-fill (Task 11.2) and the importer auto-fill (Task 11.3) import
:func:`new_record_id` rather than re-implementing it. A grep assertion in
``test_identity.py`` enforces single-source minting. The module deliberately
lives under ``scr/`` — not ``store/`` — to preserve the zero-cross-import
decoupling between the two subsystems.
"""

from __future__ import annotations

import uuid


def new_record_id() -> str:
    """Generate a fresh SCR ``record_id``.

    This is the ONLY ``record_id`` generation path in the codebase (spec015
    Task 2.4): ``str(uuid.uuid4())``. UUIDs prevent collision across concurrent
    commits and survive process restart without coordination. The write queue
    (Task 11.2) and importer (Task 11.3) import this function rather than
    re-implementing it; a grep assertion in ``test_identity.py`` enforces
    single-source.
    """
    return str(uuid.uuid4())
