"""enhance contract files for document management"""

from alembic import op
import sqlalchemy as sa

revision = "20260401_0007"
down_revision = "20260401_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contract_files", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.add_column("contract_files", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column("contract_files", sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("contract_files", sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"))
    op.add_column("contract_files", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contract_files", sa.Column("updated_by", sa.Integer(), nullable=True))
    op.add_column(
        "contract_files",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_foreign_key("fk_contract_files_owner_id_users", "contract_files", "users", ["owner_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_contract_files_updated_by_users", "contract_files", "users", ["updated_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_contract_files_owner_id", "contract_files", ["owner_id"], unique=False)
    op.create_index("ix_contract_files_category", "contract_files", ["category"], unique=False)
    op.create_index("ix_contract_files_status", "contract_files", ["status"], unique=False)

    op.execute(
        """
        UPDATE contract_files
        SET
            status = 'uploaded',
            tags = '[]',
            updated_at = created_at
        """
    )

    op.alter_column("contract_files", "tags", server_default=None)
    op.alter_column("contract_files", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_contract_files_status", table_name="contract_files")
    op.drop_index("ix_contract_files_category", table_name="contract_files")
    op.drop_index("ix_contract_files_owner_id", table_name="contract_files")
    op.drop_constraint("fk_contract_files_updated_by_users", "contract_files", type_="foreignkey")
    op.drop_constraint("fk_contract_files_owner_id_users", "contract_files", type_="foreignkey")
    op.drop_column("contract_files", "updated_at")
    op.drop_column("contract_files", "updated_by")
    op.drop_column("contract_files", "archived_at")
    op.drop_column("contract_files", "status")
    op.drop_column("contract_files", "tags")
    op.drop_column("contract_files", "category")
    op.drop_column("contract_files", "owner_id")
