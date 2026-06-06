"""add review versions and review logs"""

from alembic import op
import sqlalchemy as sa

revision = "20260401_0009"
down_revision = "20260401_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_versions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("trigger_source", sa.String(length=64), nullable=False),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("risk_items", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("overall_risk_level", sa.String(length=16), nullable=False, server_default="low"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contract_id"], ["contract_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_review_versions_id", "review_versions", ["id"], unique=False)
    op.create_index("ix_review_versions_contract_id", "review_versions", ["contract_id"], unique=False)

    op.add_column("contract_review_results", sa.Column("latest_version_id", sa.Integer(), nullable=True))
    op.add_column("contract_review_results", sa.Column("latest_version_no", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_contract_review_results_latest_version_id",
        "contract_review_results",
        "review_versions",
        ["latest_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_contract_review_results_latest_version_id", "contract_review_results", ["latest_version_id"], unique=False)

    op.create_table(
        "review_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("action_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_review_logs_id", "review_logs", ["id"], unique=False)
    op.create_index("ix_review_logs_operator_id", "review_logs", ["operator_id"], unique=False)
    op.create_index("ix_review_logs_target_id", "review_logs", ["target_id"], unique=False)
    op.create_index("ix_review_logs_target_type", "review_logs", ["target_type"], unique=False)
    op.create_index("ix_review_logs_action_type", "review_logs", ["action_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_review_logs_action_type", table_name="review_logs")
    op.drop_index("ix_review_logs_target_type", table_name="review_logs")
    op.drop_index("ix_review_logs_target_id", table_name="review_logs")
    op.drop_index("ix_review_logs_operator_id", table_name="review_logs")
    op.drop_index("ix_review_logs_id", table_name="review_logs")
    op.drop_table("review_logs")

    op.drop_index("ix_contract_review_results_latest_version_id", table_name="contract_review_results")
    op.drop_constraint("fk_contract_review_results_latest_version_id", "contract_review_results", type_="foreignkey")
    op.drop_column("contract_review_results", "latest_version_no")
    op.drop_column("contract_review_results", "latest_version_id")

    op.drop_index("ix_review_versions_contract_id", table_name="review_versions")
    op.drop_index("ix_review_versions_id", table_name="review_versions")
    op.drop_table("review_versions")
