"""Initial CRM schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('identity_tenants',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('plan', sa.String(length=50), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identity_tenants_is_deleted'), 'identity_tenants', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_identity_tenants_slug'), 'identity_tenants', ['slug'], unique=True)
    op.create_table('crm_pipelines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_pipelines_tenant_active', 'crm_pipelines', ['tenant_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_crm_pipelines_is_deleted'), 'crm_pipelines', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_crm_pipelines_tenant_id'), 'crm_pipelines', ['tenant_id'], unique=False)
    op.create_table('identity_users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'email', name='uq_tenant_user_email')
    )
    op.create_index('idx_tenant_users_role', 'identity_users', ['tenant_id', 'role'], unique=False)
    op.create_index(op.f('ix_identity_users_is_deleted'), 'identity_users', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_identity_users_tenant_id'), 'identity_users', ['tenant_id'], unique=False)
    op.create_table('crm_accounts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('industry', sa.String(length=100), nullable=True),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('annual_revenue', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('owner_id', sa.UUID(), nullable=True),
    sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['identity_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_accounts_custom_fields', 'crm_accounts', ['custom_fields'], unique=False, postgresql_using='gin')
    op.create_index('idx_crm_accounts_tenant_name', 'crm_accounts', ['tenant_id', 'name'], unique=False)
    op.create_index(op.f('ix_crm_accounts_is_deleted'), 'crm_accounts', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_crm_accounts_tenant_id'), 'crm_accounts', ['tenant_id'], unique=False)
    op.create_table('crm_leads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('company_name', sa.String(length=200), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=True),
    sa.Column('converted_account_id', sa.UUID(), nullable=True),
    sa.Column('converted_contact_id', sa.UUID(), nullable=True),
    sa.Column('converted_deal_id', sa.UUID(), nullable=True),
    sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['identity_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_leads_tenant_status', 'crm_leads', ['tenant_id', 'status'], unique=False)
    op.create_index(op.f('ix_crm_leads_is_deleted'), 'crm_leads', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_crm_leads_tenant_id'), 'crm_leads', ['tenant_id'], unique=False)
    op.create_table('crm_pipeline_stages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('pipeline_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('order', sa.Integer(), nullable=False),
    sa.Column('win_probability', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('days_until_stale', sa.Integer(), nullable=False),
    sa.Column('is_won_stage', sa.Boolean(), nullable=False),
    sa.Column('is_lost_stage', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['pipeline_id'], ['crm_pipelines.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_stages_pipeline_order', 'crm_pipeline_stages', ['tenant_id', 'pipeline_id', 'order'], unique=False)
    op.create_index(op.f('ix_crm_pipeline_stages_tenant_id'), 'crm_pipeline_stages', ['tenant_id'], unique=False)
    op.create_table('crm_contacts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('job_title', sa.String(length=100), nullable=True),
    sa.Column('account_id', sa.UUID(), nullable=True),
    sa.Column('owner_id', sa.UUID(), nullable=True),
    sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['crm_accounts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['identity_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_contacts_tenant_account', 'crm_contacts', ['tenant_id', 'account_id'], unique=False)
    op.create_index('idx_crm_contacts_tenant_email', 'crm_contacts', ['tenant_id', 'email'], unique=False)
    op.create_index(op.f('ix_crm_contacts_is_deleted'), 'crm_contacts', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_crm_contacts_tenant_id'), 'crm_contacts', ['tenant_id'], unique=False)
    op.create_table('crm_deals',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=True),
    sa.Column('contact_id', sa.UUID(), nullable=True),
    sa.Column('pipeline_id', sa.UUID(), nullable=False),
    sa.Column('stage_id', sa.UUID(), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('expected_close_date', sa.Date(), nullable=True),
    sa.Column('actual_close_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lost_reason', sa.String(length=255), nullable=True),
    sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['crm_accounts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['identity_users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['pipeline_id'], ['crm_pipelines.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['stage_id'], ['crm_pipeline_stages.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_deals_tenant_owner', 'crm_deals', ['tenant_id', 'owner_id'], unique=False)
    op.create_index('idx_crm_deals_tenant_stage', 'crm_deals', ['tenant_id', 'stage_id'], unique=False)
    op.create_index('idx_crm_deals_tenant_status', 'crm_deals', ['tenant_id', 'status'], unique=False)
    op.create_index(op.f('ix_crm_deals_is_deleted'), 'crm_deals', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_crm_deals_tenant_id'), 'crm_deals', ['tenant_id'], unique=False)
    op.create_table('crm_activities',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('activity_type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('deal_id', sa.UUID(), nullable=True),
    sa.Column('contact_id', sa.UUID(), nullable=True),
    sa.Column('account_id', sa.UUID(), nullable=True),
    sa.Column('assigned_user_id', sa.UUID(), nullable=True),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_completed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['crm_accounts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['assigned_user_id'], ['identity_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['deal_id'], ['crm_deals.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_activities_tenant_assigned', 'crm_activities', ['tenant_id', 'assigned_user_id', 'is_completed'], unique=False)
    op.create_index('idx_crm_activities_tenant_deal', 'crm_activities', ['tenant_id', 'deal_id'], unique=False)
    op.create_index(op.f('ix_crm_activities_is_deleted'), 'crm_activities', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_crm_activities_tenant_id'), 'crm_activities', ['tenant_id'], unique=False)
    op.create_table('crm_deal_stage_history',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('deal_id', sa.UUID(), nullable=False),
    sa.Column('from_stage_id', sa.UUID(), nullable=True),
    sa.Column('to_stage_id', sa.UUID(), nullable=False),
    sa.Column('changed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('duration_seconds', sa.BigInteger(), nullable=True),
    sa.Column('transitioned_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['changed_by_user_id'], ['identity_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['deal_id'], ['crm_deals.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['from_stage_id'], ['crm_pipeline_stages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['identity_tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_stage_id'], ['crm_pipeline_stages.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crm_stage_history_deal_transition', 'crm_deal_stage_history', ['tenant_id', 'deal_id', 'transitioned_at'], unique=False)
    op.create_index(op.f('ix_crm_deal_stage_history_deal_id'), 'crm_deal_stage_history', ['deal_id'], unique=False)
    op.create_index(op.f('ix_crm_deal_stage_history_tenant_id'), 'crm_deal_stage_history', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crm_deal_stage_history_tenant_id'), table_name='crm_deal_stage_history')
    op.drop_index(op.f('ix_crm_deal_stage_history_deal_id'), table_name='crm_deal_stage_history')
    op.drop_index('idx_crm_stage_history_deal_transition', table_name='crm_deal_stage_history')
    op.drop_table('crm_deal_stage_history')
    op.drop_index(op.f('ix_crm_activities_tenant_id'), table_name='crm_activities')
    op.drop_index(op.f('ix_crm_activities_is_deleted'), table_name='crm_activities')
    op.drop_index('idx_crm_activities_tenant_deal', table_name='crm_activities')
    op.drop_index('idx_crm_activities_tenant_assigned', table_name='crm_activities')
    op.drop_table('crm_activities')
    op.drop_index(op.f('ix_crm_deals_tenant_id'), table_name='crm_deals')
    op.drop_index(op.f('ix_crm_deals_is_deleted'), table_name='crm_deals')
    op.drop_index('idx_crm_deals_tenant_status', table_name='crm_deals')
    op.drop_index('idx_crm_deals_tenant_stage', table_name='crm_deals')
    op.drop_index('idx_crm_deals_tenant_owner', table_name='crm_deals')
    op.drop_table('crm_deals')
    op.drop_index(op.f('ix_crm_contacts_tenant_id'), table_name='crm_contacts')
    op.drop_index(op.f('ix_crm_contacts_is_deleted'), table_name='crm_contacts')
    op.drop_index('idx_crm_contacts_tenant_email', table_name='crm_contacts')
    op.drop_index('idx_crm_contacts_tenant_account', table_name='crm_contacts')
    op.drop_table('crm_contacts')
    op.drop_index(op.f('ix_crm_pipeline_stages_tenant_id'), table_name='crm_pipeline_stages')
    op.drop_index('idx_crm_stages_pipeline_order', table_name='crm_pipeline_stages')
    op.drop_table('crm_pipeline_stages')
    op.drop_index(op.f('ix_crm_leads_tenant_id'), table_name='crm_leads')
    op.drop_index(op.f('ix_crm_leads_is_deleted'), table_name='crm_leads')
    op.drop_index('idx_crm_leads_tenant_status', table_name='crm_leads')
    op.drop_table('crm_leads')
    op.drop_index(op.f('ix_crm_accounts_tenant_id'), table_name='crm_accounts')
    op.drop_index(op.f('ix_crm_accounts_is_deleted'), table_name='crm_accounts')
    op.drop_index('idx_crm_accounts_tenant_name', table_name='crm_accounts')
    op.drop_index('idx_crm_accounts_custom_fields', table_name='crm_accounts', postgresql_using='gin')
    op.drop_table('crm_accounts')
    op.drop_index(op.f('ix_identity_users_tenant_id'), table_name='identity_users')
    op.drop_index(op.f('ix_identity_users_is_deleted'), table_name='identity_users')
    op.drop_index('idx_tenant_users_role', table_name='identity_users')
    op.drop_table('identity_users')
    op.drop_index(op.f('ix_crm_pipelines_tenant_id'), table_name='crm_pipelines')
    op.drop_index(op.f('ix_crm_pipelines_is_deleted'), table_name='crm_pipelines')
    op.drop_index('idx_crm_pipelines_tenant_active', table_name='crm_pipelines')
    op.drop_table('crm_pipelines')
    op.drop_index(op.f('ix_identity_tenants_slug'), table_name='identity_tenants')
    op.drop_index(op.f('ix_identity_tenants_is_deleted'), table_name='identity_tenants')
    op.drop_table('identity_tenants')
