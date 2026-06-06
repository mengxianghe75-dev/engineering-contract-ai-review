"""add parse status to contract parse results"""

from alembic import op
import sqlalchemy as sa

revision = "20260330_0005"
down_revision = "20260330_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_parse_results",
        sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="completed"),
    )
    op.add_column(
        "contract_parse_results",
        sa.Column("parse_error", sa.Text(), nullable=True),
    )
    op.alter_column("contract_parse_results", "parse_status", server_default=None)


def downgrade() -> None:
    op.drop_column("contract_parse_results", "parse_error")
    op.drop_column("contract_parse_results", "parse_status")
