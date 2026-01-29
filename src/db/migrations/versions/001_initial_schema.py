"""Initial schema with User, Conversation, Participant, Message tables.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # Create users table
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            display_name VARCHAR(100) NOT NULL,
            avatar_url VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create conversations table
    op.execute("""
        CREATE TABLE conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create index for sorting by recent activity
    op.execute("""
        CREATE INDEX idx_conversation_updated_at
        ON conversations (updated_at DESC)
    """)

    # Create participants table (junction table)
    op.execute("""
        CREATE TABLE participants (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_read_at TIMESTAMPTZ,
            PRIMARY KEY (user_id, conversation_id)
        )
    """)

    # Create indexes for participants
    op.execute("CREATE INDEX idx_participant_user_id ON participants (user_id)")
    op.execute("CREATE INDEX idx_participant_conv_id ON participants (conversation_id)")

    # Create messages table
    op.execute("""
        CREATE TABLE messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL CHECK (length(content) <= 10000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status VARCHAR(20) NOT NULL DEFAULT 'sent'
                CHECK (status IN ('sending', 'sent', 'delivered', 'failed'))
        )
    """)

    # Create indexes for messages
    op.execute("""
        CREATE INDEX idx_message_conv_created
        ON messages (conversation_id, created_at DESC)
    """)
    op.execute("CREATE INDEX idx_message_sender ON messages (sender_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS participants CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
