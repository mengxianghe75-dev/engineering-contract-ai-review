"""add contract upload version grouping"""

from alembic import op
import sqlalchemy as sa

revision = "20260402_0012"
down_revision = "20260402_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("contract_files", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("version_root_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("upload_version_no", sa.Integer(), nullable=False, server_default="1"),
        )
        batch_op.create_foreign_key(
            "fk_contract_files_version_root_id",
            "contract_files",
            ["version_root_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_contract_files_version_root_id", ["version_root_id"], unique=False)
        batch_op.create_index("ix_contract_files_upload_version_no", ["upload_version_no"], unique=False)

    op.execute(
        """
        UPDATE contract_files
        SET
            version_root_id = id,
            upload_version_no = 1
        """
    )

    with op.batch_alter_table("contract_files", recreate="auto") as batch_op:
        batch_op.alter_column("upload_version_no", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("contract_files", recreate="auto") as batch_op:
        batch_op.drop_index("ix_contract_files_upload_version_no")
        batch_op.drop_index("ix_contract_files_version_root_id")
        batch_op.drop_constraint("fk_contract_files_version_root_id", type_="foreignkey")
        batch_op.drop_column("upload_version_no")
        batch_op.drop_column("version_root_id")
