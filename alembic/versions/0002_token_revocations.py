"""Persist revoked access tokens."""
from alembic import op
import sqlalchemy as sa

revision = '0002_token_revocations'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('identity_revoked_tokens',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('token_hash')
    )
    op.create_index(op.f('ix_identity_revoked_tokens_expires_at'), 'identity_revoked_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_identity_revoked_tokens_expires_at'), table_name='identity_revoked_tokens')
    op.drop_table('identity_revoked_tokens')
