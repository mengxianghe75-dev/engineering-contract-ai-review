"""add review version runtime status fields"""

from alembic import op
import sqlalchemy as sa

revision = "20260402_0011"
down_revision = "20260401_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_versions", sa.Column("summary_provider", sa.String(length=64), nullable=True))
    op.add_column("review_versions", sa.Column("summary_success", sa.Boolean(), nullable=True))
    op.add_column("review_versions", sa.Column("summary_message", sa.Text(), nullable=True))
    op.add_column("review_versions", sa.Column("risk_provider", sa.String(length=64), nullable=True))
    op.add_column("review_versions", sa.Column("risk_success", sa.Boolean(), nullable=True))
    op.add_column("review_versions", sa.Column("risk_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("review_versions", "risk_message")
    op.drop_column("review_versions", "risk_success")
    op.drop_column("review_versions", "risk_provider")
    op.drop_column("review_versions", "summary_message")
    op.drop_column("review_versions", "summary_success")
    op.drop_column("review_versions", "summary_provider")
