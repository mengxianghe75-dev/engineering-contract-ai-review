"""create contract review results table"""

from alembic import op
import sqlalchemy as sa

revision = "20260329_0003"
down_revision = "20260329_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_review_results",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("contract_file_id", sa.Integer(), nullable=False),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contract_file_id"], ["contract_files.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_contract_review_results_id", "contract_review_results", ["id"], unique=False)
    op.create_index(
        "ix_contract_review_results_contract_file_id",
        "contract_review_results",
        ["contract_file_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_contract_review_results_contract_file_id", table_name="contract_review_results")
    op.drop_index("ix_contract_review_results_id", table_name="contract_review_results")
    op.drop_table("contract_review_results")
