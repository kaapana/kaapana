"""
Transforms the initial single-table workflow into the revision-history model:
- Workflow PK switches from int to UUID.
- New `workflow_revisions` table holds (definition, workflow_parameters, labels)
  per increment. Existing workflow rows are promoted to a single revision each.
- `workflow_label` is replaced by `workflow_revision_label` (M:M from revisions).
- `workflow_runs.workflow_id` and `tasks.workflow_id` are repointed to
  `workflow_revision_id` (UUID).
- Partial unique index on `workflows.title WHERE removed = false` replaces the
  old `UNIQUE(title, version)` constraint.

Postgres-only. Downgrade is not supported (data shape is irreversible).

Revision ID: 4f9a2b1d7e3c
Revises: 721d0352a128
Create Date: 2026-06-05
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4f9a2b1d7e3c"
down_revision: Union[str, None] = "721d0352a128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # gen_random_uuid() lives in pgcrypto on older Postgres; on 13+ it is built in.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 1. workflows: add id_new UUID; will become the new PK once children are repointed.
    op.add_column(
        "workflows",
        sa.Column(
            "id_new",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )

    # workflow_engine becomes NOT NULL.
    op.execute(
        "UPDATE workflows SET workflow_engine = 'dummy' WHERE workflow_engine IS NULL"
    )
    op.alter_column(
        "workflows", "workflow_engine", existing_type=sa.String(), nullable=False
    )

    # 2. workflow_revisions table.
    op.create_table(
        "workflow_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("increment", sa.Integer(), nullable=False),
        sa.Column("definition", sa.String(), nullable=True),
        sa.Column(
            "workflow_parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workflow_id", "increment"),
    )
    op.create_index(
        "ix_workflow_revisions_id", "workflow_revisions", ["id"], unique=False
    )
    op.create_index(
        "ix_workflow_revisions_workflow_id",
        "workflow_revisions",
        ["workflow_id"],
        unique=False,
    )

    # 3. Backfill workflow_revisions, one row per existing workflow.
    workflows = (
        bind.execute(
            sa.text(
                "SELECT id, id_new, version, definition, workflow_parameters, created_at "
                "FROM workflows"
            )
        )
        .mappings()
        .all()
    )

    int_to_revision_uuid: dict[int, uuid.UUID] = {}
    for w in workflows:
        rev_uuid = uuid.uuid4()
        params_value = (
            json.dumps(w["workflow_parameters"])
            if w["workflow_parameters"] is not None
            else None
        )
        bind.execute(
            sa.text(
                "INSERT INTO workflow_revisions "
                "(id, workflow_id, increment, definition, workflow_parameters, created_at) "
                "VALUES (:rev_id, :wf_id, :inc, :def, CAST(:params AS jsonb), :ts)"
            ),
            {
                "rev_id": rev_uuid,
                "wf_id": w["id_new"],
                "inc": w["version"] or 1,
                "def": w["definition"],
                "params": params_value,
                "ts": w["created_at"],
            },
        )
        int_to_revision_uuid[w["id"]] = rev_uuid

    # 4. workflow_revisions

    # 5. Repoint tasks: workflow_id (int -> workflows.id) becomes workflow_revision_id (UUID -> workflow_revisions.id).
    op.add_column(
        "tasks",
        sa.Column("workflow_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    for old_int, rev_uuid in int_to_revision_uuid.items():
        bind.execute(
            sa.text(
                "UPDATE tasks SET workflow_revision_id = :r WHERE workflow_id = :w"
            ),
            {"r": rev_uuid, "w": old_int},
        )

    # 6. Repoint workflow_runs the same way.
    op.add_column(
        "workflow_runs",
        sa.Column("workflow_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # `updated_at` already exists from the initial migration (721d0352a128), only backfill it for legacy rows where it was never populated.
    bind.execute(
        sa.text(
            "UPDATE workflow_runs SET updated_at = created_at WHERE updated_at IS NULL"
        )
    )
    for old_int, rev_uuid in int_to_revision_uuid.items():
        bind.execute(
            sa.text(
                "UPDATE workflow_runs SET workflow_revision_id = :r WHERE workflow_id = :w"
            ),
            {"r": rev_uuid, "w": old_int},
        )

    # 7. workflow_revision_label replaces workflow_label.
    op.create_table(
        "workflow_revision_label",
        sa.Column(
            "workflow_revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_revisions.id"),
            primary_key=True,
        ),
        sa.Column(
            "label_id",
            sa.Integer(),
            sa.ForeignKey("labels.id"),
            primary_key=True,
        ),
    )
    bind.execute(
        sa.text(
            "INSERT INTO workflow_revision_label (workflow_revision_id, label_id) "
            "SELECT wr.id, wl.label_id FROM workflow_label wl "
            "JOIN workflow_revisions wr ON wr.workflow_id = ("
            "  SELECT w.id_new FROM workflows w WHERE w.id = wl.workflow_id"
            ") ON CONFLICT DO NOTHING"
        )
    )

    # 8. Drop old FK columns and constraints from tasks / workflow_runs / workflow_label.
    op.drop_table("workflow_label")
    op.drop_constraint(
        "workflow_runs_workflow_id_fkey", "workflow_runs", type_="foreignkey"
    )
    op.drop_column("workflow_runs", "workflow_id")
    op.drop_constraint("tasks_workflow_id_fkey", "tasks", type_="foreignkey")
    op.drop_column("tasks", "workflow_id")

    # 9. Drop old constraints / index / columns on workflows.
    op.drop_constraint("workflows_title_version_key", "workflows", type_="unique")
    op.drop_index("ix_workflows_id", table_name="workflows")
    op.drop_constraint("workflows_pkey", "workflows", type_="primary")
    op.drop_column("workflows", "id")
    op.drop_column("workflows", "version")
    op.drop_column("workflows", "definition")
    op.drop_column("workflows", "workflow_parameters")
    op.alter_column(
        "workflows",
        "id_new",
        new_column_name="id",
        server_default=sa.text("gen_random_uuid()"),
    )
    op.create_primary_key("workflows_pkey", "workflows", ["id"])
    op.create_index("ix_workflows_id", "workflows", ["id"], unique=False)

    # 9b. Now that workflows.id is the (unique) PK, add the workflow_revisions FK deferred from step 4
    op.create_foreign_key(
        "workflow_revisions_workflow_id_fkey",
        "workflow_revisions",
        "workflows",
        ["workflow_id"],
        ["id"],
    )

    # 10. Add new FKs on the repointed columns (tasks, workflow_runs).
    op.create_foreign_key(
        "tasks_workflow_revision_id_fkey",
        "tasks",
        "workflow_revisions",
        ["workflow_revision_id"],
        ["id"],
    )
    op.create_foreign_key(
        "workflow_runs_workflow_revision_id_fkey",
        "workflow_runs",
        "workflow_revisions",
        ["workflow_revision_id"],
        ["id"],
    )
    # Orphan rows (tasks/workflow_runs whose old workflow_id pointed at a workflow row that no longer exists) cannot be backfilled and must be removed.
    deleted_tasks = bind.execute(
        sa.text("DELETE FROM tasks WHERE workflow_revision_id IS NULL")
    ).rowcount
    deleted_runs = bind.execute(
        sa.text("DELETE FROM workflow_runs WHERE workflow_revision_id IS NULL")
    ).rowcount
    if deleted_tasks or deleted_runs:
        op.execute(
            sa.text(
                "DO $$ BEGIN RAISE NOTICE 'Deleted % orphan tasks and % orphan "
                "workflow_runs during 4f9a2b1d7e3c migration', "
                f"{int(deleted_tasks)}, {int(deleted_runs)}; END $$;"
            )
        )

    op.alter_column("tasks", "workflow_revision_id", nullable=False)
    op.alter_column("workflow_runs", "workflow_revision_id", nullable=False)
    op.create_index(
        "ix_workflow_runs_workflow_revision_id",
        "workflow_runs",
        ["workflow_revision_id"],
        unique=False,
    )

    # 11. Partial unique index on workflows.title (active only).
    op.create_index(
        "uq_workflows_title_active",
        "workflows",
        ["title"],
        unique=True,
        postgresql_where=sa.text("removed = false"),
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade is not supported: this migration is destructive "
        "(workflow PK swap, table restructure, label association move)."
    )
