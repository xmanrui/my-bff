"""Add optimized index for message history queries.

Revision ID: 002_message_history_index
Revises: 001_initial_schema
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_message_history_index"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The index idx_message_conv_created already exists from initial migration
    # This migration adds a covering index for better query performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_message_history_query
        ON messages (conversation_id, created_at DESC)
        INCLUDE (id, sender_id, content, status)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_message_history_query")
