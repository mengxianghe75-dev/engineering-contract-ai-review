"""add system settings table"""

from alembic import op
import sqlalchemy as sa

revision = "20260401_0010"
down_revision = "20260401_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_system_settings_id", "system_settings", ["id"], unique=False)
    op.create_index("ix_system_settings_setting_key", "system_settings", ["setting_key"], unique=True)
    op.alter_column("system_settings", "is_secret", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_system_settings_setting_key", table_name="system_settings")
    op.drop_index("ix_system_settings_id", table_name="system_settings")
    op.drop_table("system_settings")
