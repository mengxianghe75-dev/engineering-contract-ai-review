"""create contract upload tables"""

from alembic import op
import sqlalchemy as sa

revision = "20260329_0002"
down_revision = "20260329_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_files",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_contract_files_id", "contract_files", ["id"], unique=False)
    op.create_index("ix_contract_files_stored_filename", "contract_files", ["stored_filename"], unique=True)

    op.create_table(
        "contract_parse_results",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("contract_file_id", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contract_file_id"], ["contract_files.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_contract_parse_results_id", "contract_parse_results", ["id"], unique=False)
    op.create_index(
        "ix_contract_parse_results_contract_file_id",
        "contract_parse_results",
        ["contract_file_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_contract_parse_results_contract_file_id", table_name="contract_parse_results")
    op.drop_index("ix_contract_parse_results_id", table_name="contract_parse_results")
    op.drop_table("contract_parse_results")
    op.drop_index("ix_contract_files_stored_filename", table_name="contract_files")
    op.drop_index("ix_contract_files_id", table_name="contract_files")
    op.drop_table("contract_files")
