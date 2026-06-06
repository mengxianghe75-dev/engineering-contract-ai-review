"""add parse metadata to contract parse results"""

from alembic import op
import sqlalchemy as sa

revision = "20260330_0004"
down_revision = "20260329_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_parse_results",
        sa.Column("parse_mode", sa.String(length=32), nullable=False, server_default="text"),
    )
    op.add_column(
        "contract_parse_results",
        sa.Column("parse_notice", sa.Text(), nullable=True),
    )
    op.alter_column("contract_parse_results", "parse_mode", server_default=None)


def downgrade() -> None:
    op.drop_column("contract_parse_results", "parse_notice")
    op.drop_column("contract_parse_results", "parse_mode")
