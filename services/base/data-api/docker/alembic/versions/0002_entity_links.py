"""entity_links graph table

Revision ID: 0002_entity_links
Revises: 0001_initial
Create Date: 2026-05-20 00:00:00.000000

Replaces the single-parent `data_entities.parent_id` column with a directed
graph table `entity_links` that carries typed edges and JSONB properties.
Existing parent_id rows are backfilled as edges of type 'contains'
(parent_id becomes the link source, the row's id becomes the target).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_entity_links"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("link_type", sa.String(length=64), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_id", "target_id", "link_type", name="uq_entity_links_triple"
        ),
        sa.CheckConstraint(
            "source_id <> target_id", name="ck_entity_links_no_self_loop"
        ),
    )
    op.create_index(
        "ix_entity_links_source",
        "entity_links",
        ["source_id", "link_type"],
        unique=False,
    )
    op.create_index(
        "ix_entity_links_target",
        "entity_links",
        ["target_id", "link_type"],
        unique=False,
    )

    # Backfill existing parent_id rows into entity_links of type 'contains'.
    # Old parent_id became the source; the row itself becomes the target.
    op.execute("""
        INSERT INTO entity_links (id, source_id, target_id, link_type, properties, created_at)
        SELECT gen_random_uuid(), parent_id, id, 'contains', '{}'::jsonb, now()
        FROM data_entities
        WHERE parent_id IS NOT NULL
        """)

    op.drop_constraint("fk_data_entities_parent", "data_entities", type_="foreignkey")
    op.drop_index("ix_data_entities_parent_id", table_name="data_entities")
    op.drop_column("data_entities", "parent_id")


def downgrade() -> None:
    # Best-effort restoration: only the single-parent slice of the graph fits
    # back into the old column. Refuse to drop link data we can't represent.
    bind = op.get_bind()
    multi_parent = bind.execute(sa.text("""
            SELECT 1 FROM (
                SELECT target_id, COUNT(*) AS n
                FROM entity_links
                WHERE link_type = 'contains'
                GROUP BY target_id
            ) c WHERE c.n > 1
            LIMIT 1
            """)).first()
    if multi_parent is not None:
        raise RuntimeError(
            "Cannot downgrade: some entities have more than one incoming "
            "'contains' link. Resolve to a single parent before downgrading."
        )

    op.add_column(
        "data_entities",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("""
        UPDATE data_entities AS de
        SET parent_id = el.source_id
        FROM entity_links AS el
        WHERE el.target_id = de.id AND el.link_type = 'contains'
        """)
    op.create_foreign_key(
        "fk_data_entities_parent",
        "data_entities",
        "data_entities",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_data_entities_parent_id", "data_entities", ["parent_id"], unique=False
    )

    op.drop_index("ix_entity_links_target", table_name="entity_links")
    op.drop_index("ix_entity_links_source", table_name="entity_links")
    op.drop_table("entity_links")
