"""add review rules table"""

from alembic import op
import sqlalchemy as sa

revision = "20260401_0008"
down_revision = "20260401_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_rules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("risk_type", sa.String(length=100), nullable=False),
        sa.Column("condition_type", sa.String(length=32), nullable=False),
        sa.Column("condition_value", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("contract_type_scope", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_review_rules_id", "review_rules", ["id"], unique=False)
    op.create_index("ix_review_rules_rule_code", "review_rules", ["rule_code"], unique=True)
    op.create_index("ix_review_rules_condition_type", "review_rules", ["condition_type"], unique=False)
    op.create_index("ix_review_rules_risk_level", "review_rules", ["risk_level"], unique=False)
    op.create_index("ix_review_rules_priority", "review_rules", ["priority"], unique=False)

    review_rules = sa.table(
        "review_rules",
        sa.column("name", sa.String(length=100)),
        sa.column("rule_code", sa.String(length=64)),
        sa.column("risk_type", sa.String(length=100)),
        sa.column("condition_type", sa.String(length=32)),
        sa.column("condition_value", sa.Text()),
        sa.column("risk_level", sa.String(length=16)),
        sa.column("suggestion", sa.Text()),
        sa.column("priority", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_deleted", sa.Boolean()),
        sa.column("contract_type_scope", sa.Text()),
    )
    op.bulk_insert(
        review_rules,
        [
            {
                "name": "付款条款风险",
                "rule_code": "payment_terms_risk",
                "risk_type": "付款条件偏严或付款节点不明确，可能导致回款滞后。",
                "condition_type": "contains_any",
                "condition_value": '["结清","竣工验收合格后支付","无预付款","甲方审核后支付"]',
                "risk_level": "high",
                "suggestion": "补充预付款、进度款和付款时间上限，明确逾期付款责任。",
                "priority": 10,
                "is_active": True,
                "is_deleted": False,
                "contract_type_scope": None,
            },
            {
                "name": "结算条款风险",
                "rule_code": "settlement_terms_risk",
                "risk_type": "结算依据单方控制或结算周期不清，存在价款争议风险。",
                "condition_type": "contains_any",
                "condition_value": '["最终结算以甲方审定为准","结算以审计结果为准","另行协商"]',
                "risk_level": "medium",
                "suggestion": "明确结算资料、审核期限和逾期视为认可规则。",
                "priority": 20,
                "is_active": True,
                "is_deleted": False,
                "contract_type_scope": None,
            },
            {
                "name": "工期责任风险",
                "rule_code": "schedule_liability_risk",
                "risk_type": "工期责任偏重乙方，且缺少顺延或免责条件。",
                "condition_type": "contains_any",
                "condition_value": '["每延误一日","工期不得顺延","自行承担赶工"]',
                "risk_level": "high",
                "suggestion": "增加顺延条件、甲方原因停工处理和不可抗力条款。",
                "priority": 30,
                "is_active": True,
                "is_deleted": False,
                "contract_type_scope": None,
            },
        ],
    )

    op.alter_column("review_rules", "priority", server_default=None)
    op.alter_column("review_rules", "is_active", server_default=None)
    op.alter_column("review_rules", "is_deleted", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_review_rules_priority", table_name="review_rules")
    op.drop_index("ix_review_rules_risk_level", table_name="review_rules")
    op.drop_index("ix_review_rules_condition_type", table_name="review_rules")
    op.drop_index("ix_review_rules_rule_code", table_name="review_rules")
    op.drop_index("ix_review_rules_id", table_name="review_rules")
    op.drop_table("review_rules")
