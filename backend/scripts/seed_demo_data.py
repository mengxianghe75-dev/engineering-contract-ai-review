"""
工程合同 AI 审查助手 — 演示数据种子脚本

用法：
    cd backend
    python scripts/seed_demo_data.py

功能：
    1. 创建 3 个演示 PDF 合同文件
    2. 创建演示用户（reviewer、viewer）
    3. 创建演示审查规则
    4. 写入合同、解析结果、审查结果、审查版本、操作日志
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add backend root to path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from passlib.hash import bcrypt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from app.core.config import settings, settings_upload_path
from app.db.session import SessionLocal, Base
from app.models import (
    User, Role, UserRole, ReviewRule,
    ContractFile, ContractParseResult, ContractReviewResult,
    ReviewVersion, ReviewLog,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def make_pdf(filename: str, title: str, content: str) -> str:
    """Generate a PDF file and return the stored filename."""
    settings_upload_path.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}.pdf"
    filepath = settings_upload_path / stored

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ContractTitle",
        fontSize=16,
        alignment=1,  # center
        spaceAfter=12,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="ContractBody",
        fontSize=10,
        spaceAfter=6,
        leading=14,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    ))

    story = [Paragraph(title, styles["ContractTitle"])]
    story.append(Spacer(1, 6))

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue
        if line.startswith("第") and "条" in line:
            story.append(Paragraph(line, styles["SectionTitle"]))
        else:
            story.append(Paragraph(line, styles["ContractBody"]))

    doc.build(story)
    return stored


# ── Demo Contracts ────────────────────────────────────────────────────────────

CONTRACT_1_TEXT = """
合同名称：某市滨江大桥施工总承包合同
合同编号：BJ-2026-001
项目名称：某市滨江大桥工程
合同类型：施工合同
签订日期：2026年1月15日
合同金额：人民币贰仟伍佰万元整（￥25,000,000.00）

甲方：某市交通投资建设集团有限公司
乙方：中建第五工程局有限公司

一、工程概况
本工程位于某市滨江新区，全长3.2公里，包含主桥及引桥施工。

二、工作内容
详见附件工程量清单及施工图纸。乙方须按照甲方要求完成全部施工任务。

三、工期
总工期为360日历天。工期不得顺延，每延误一日，乙方须向甲方支付合同总价万分之五的违约金，且自行承担赶工费用。

四、付款方式
本工程无预付款。工程进度款按月支付，甲方审核后三十日内支付。工程竣工后全部结清，竣工验收合格后支付至97%。

五、质保金
本工程质保金为结算总价的3%，质保期自竣工验收合格之日起24个月。质保期满后经甲方验收合格后无息返还。

六、变更与签证
工程变更须经甲方书面确认，签证程序详见附件。

七、发票与税务
乙方须按甲方要求提供增值税专用发票。

八、违约责任
乙方逾期交付的，甲方有权按日收取违约金。因乙方原因造成工程质量不合格的，乙方承担全部责任。

九、争议解决
因本合同引起的争议，提交甲方所在地人民法院管辖。

十、合同解除
甲方有权在乙方严重违约时单方解除合同，解除后已完成工程量由甲方审定后结算。
"""

CONTRACT_2_TEXT = """
合同名称：城南片区市政道路工程分包合同
合同编号：CN-2026-002
项目名称：城南片区市政道路工程
合同类型：分包合同
签订日期：2026年2月20日
合同金额：人民币捌佰万元整（￥8,000,000.00）

甲方：中建第三工程局有限公司
乙方：某省路桥工程有限公司

一、工程概况
本工程为城南片区市政道路工程，包含道路工程、排水工程、照明工程等。

二、工作内容
承包范围：K0+000至K3+500段道路及附属工程。

三、工期
总工期180日历天。因不可抗力或甲方原因导致延误的，工期可相应顺延。

四、付款方式
预付款为合同总价的10%，按月进度支付工程款。甲方审核后十五日内支付进度款。最终结算以双方协商为准。

五、质保金
工程质保金为2%，质保期12个月。质保金返还时间另行协商。

六、变更签证
工程变更须按甲方程序提交书面申请，经双方签证确认后方可实施。

七、发票与税务
乙方须提供符合要求的发票。税率调整由双方协商处理。

八、违约责任
双方应严格按合同约定履行义务。任何一方违约的，应承担相应的违约责任。

九、争议解决
争议应优先协商解决，协商不成的提交工程所在地人民法院管辖。

十、合同解除
任何一方严重违约的，守约方有权书面通知后解除合同。解除后按已完成工程量结算。
"""

CONTRACT_3_TEXT = """
合同名称：高新区智能制造基地建设工程施工合同
合同编号：GQ-2026-003
项目名称：高新区智能制造基地建设工程
合同类型：施工合同
签订日期：2026年3月10日
合同金额：人民币壹亿贰仟万元整（￥120,000,000.00）

甲方：高新区科技产业发展有限公司
乙方：中铁建工集团有限公司

一、工程概况
本工程位于高新区创新产业园，总建筑面积85,000平方米，包含研发楼、生产车间及配套设施。

二、工作内容
乙方负责施工图纸范围内全部土建、安装及装饰装修工程。具体工程范围详见附件清单。

三、工期
总工期540日历天。因甲方原因或不可抗力导致停工的，工期相应顺延。乙方应编制详细进度计划报甲方审批。

四、付款方式
预付款为合同总价的15%，按工程节点支付。甲方收到乙方请款报告后14日内完成审核并支付进度款。工程竣工验收合格后支付至97%。

五、质保金
质保金为结算总价的3%，质保期24个月。质保期满后30日内无息返还。

六、变更与签证
工程变更须按甲方书面签证确认程序执行，变更价款按合同约定单价计算。

七、发票与税务
乙方按甲方要求提供增值税专用发票，开票时间为付款前5个工作日。

八、违约责任
双方违约责任对等。任何一方违约的，违约方须承担由此造成的直接损失。

九、争议解决
因本合同引起的争议，提交工程所在地人民法院管辖。

十、合同解除
合同解除须满足以下条件：一方严重违约经书面催告后30日内仍未纠正的，守约方可书面通知解除合同。解除后15日内完成结算。
"""

CONTRACTS = [
    {
        "filename": "某市滨江大桥施工总承包合同.pdf",
        "title": "某市滨江大桥施工总承包合同",
        "content": CONTRACT_1_TEXT,
        "category": "施工合同",
        "tags": ["重点项目", "桥梁工程"],
        "owner_id": 1,  # admin
    },
    {
        "filename": "城南片区市政道路工程分包合同.pdf",
        "title": "城南片区市政道路工程分包合同",
        "content": CONTRACT_2_TEXT,
        "category": "分包合同",
        "tags": ["市政道路", "城南片区"],
        "owner_id": 1,
    },
    {
        "filename": "高新区智能制造基地建设工程施工合同.pdf",
        "title": "高新区智能制造基地建设工程施工合同",
        "content": CONTRACT_3_TEXT,
        "category": "施工合同",
        "tags": ["智能制造", "高新区"],
        "owner_id": 1,
    },
]

# ── Demo Rules ────────────────────────────────────────────────────────────────

DEMO_RULES = [
    {
        "name": "付款条款风险",
        "rule_code": "payment_terms_risk",
        "risk_type": "付款条件偏严或付款节点不明确，可能导致回款滞后。",
        "condition_type": "contains_any",
        "condition_value": '["结清","无预付款","竣工验收合格后支付"]',
        "risk_level": "high",
        "suggestion": "补充预付款和节点支付约定，明确逾期付款责任。",
        "priority": 10,
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
        "contract_type_scope": None,
    },
    {
        "name": "工期责任风险",
        "rule_code": "schedule_liability_risk",
        "risk_type": "工期责任偏重乙方，且缺少顺延或免责条件。",
        "condition_type": "keyword",
        "condition_value": "每延误一日",
        "risk_level": "high",
        "suggestion": "增加顺延条件、甲方原因停工处理和不可抗力条款。",
        "priority": 15,
        "contract_type_scope": None,
    },
    {
        "name": "违约责任不对等",
        "rule_code": "unbalanced_breach_liability",
        "risk_type": "违约责任明显偏向一方，存在责任失衡风险。",
        "condition_type": "keyword",
        "condition_value": "乙方承担全部责任",
        "risk_level": "high",
        "suggestion": "补充甲方违约责任和双方对等责任机制。",
        "priority": 12,
        "contract_type_scope": None,
    },
    {
        "name": "质保金风险",
        "rule_code": "retention_money_risk",
        "risk_type": "存在质保金约定但返还条件或期限不明。",
        "condition_type": "keyword",
        "condition_value": "质保金",
        "risk_level": "medium",
        "suggestion": "明确质保金比例、返还时间和返还前提。",
        "priority": 25,
        "contract_type_scope": None,
    },
    {
        "name": "争议解决风险",
        "rule_code": "dispute_resolution_risk",
        "risk_type": "争议解决地点对一方明显不利或条款不完整。",
        "condition_type": "keyword",
        "condition_value": "甲方所在地人民法院",
        "risk_level": "medium",
        "suggestion": "优先约定工程所在地或合同履行地争议解决方式。",
        "priority": 30,
        "contract_type_scope": None,
    },
    {
        "name": "合同解除条款风险",
        "rule_code": "termination_clause_risk",
        "risk_type": "解除权约定偏单方或解除后处理不清。",
        "condition_type": "keyword",
        "condition_value": "甲方有权",
        "risk_level": "medium",
        "suggestion": "明确双方解除条件、通知期限和解除后结算规则。",
        "priority": 35,
        "contract_type_scope": None,
    },
]


# ── Main Script ───────────────────────────────────────────────────────────────

def seed_demo_data():
    db = SessionLocal()
    try:
        print("=== 开始写入演示数据 ===\n")

        # 1. Create demo users
        print("[1/6] 创建演示用户...")
        for username, password, role_code in [
            ("zhang_reviewer", "Reviewer123", "reviewer"),
            ("li_viewer", "Viewer12345", "viewer"),
        ]:
            existing = db.query(User).filter_by(username=username).first()
            if existing:
                print(f"  用户 {username} 已存在，跳过")
                continue
            user = User(
                username=username,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            db.flush()

            role = db.query(Role).filter_by(code=role_code).first()
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id))
            print(f"  已创建用户 {username}（{role_code}）")

        db.commit()
        print()

        # 2. Create demo rules
        print("[2/6] 创建演示规则...")
        admin = db.query(User).filter_by(username="admin").first()
        created_by_id = admin.id if admin else None

        for rule_data in DEMO_RULES:
            existing = db.query(ReviewRule).filter_by(rule_code=rule_data["rule_code"]).first()
            if existing:
                print(f"  规则 {rule_data['rule_code']} 已存在，跳过")
                continue
            rule = ReviewRule(
                name=rule_data["name"],
                rule_code=rule_data["rule_code"],
                risk_type=rule_data["risk_type"],
                condition_type=rule_data["condition_type"],
                condition_value=rule_data["condition_value"],
                risk_level=rule_data["risk_level"],
                suggestion=rule_data["suggestion"],
                priority=rule_data["priority"],
                is_active=True,
                contract_type_scope=rule_data["contract_type_scope"],
                created_by=created_by_id,
            )
            db.add(rule)
            print(f"  已创建规则 {rule_data['rule_code']}")

        db.commit()
        print()

        # 3. Generate PDFs & create contracts
        print("[3/6] 生成演示合同PDF并写入数据库...")
        contract_files = []
        for i, c in enumerate(CONTRACTS):
            # Check if file already exists by filename
            existing = db.query(ContractFile).filter_by(original_filename=c["filename"]).first()
            if existing:
                print(f"  合同 {c['filename']} 已存在，跳过")
                contract_files.append(existing)
                continue

            stored_filename = make_pdf(c["filename"], c["title"], c["content"])
            file_path = settings_upload_path / stored_filename
            file_bytes = file_path.read_bytes()

            contract_file = ContractFile(
                original_filename=c["filename"],
                stored_filename=stored_filename,
                file_path=str(file_path),
                content_type="application/pdf",
                file_size=len(file_bytes),
                owner_id=c["owner_id"],
                category=c["category"],
                tags=c["tags"],
                status="uploaded",
                updated_by=c["owner_id"],
            )
            db.add(contract_file)
            db.flush()

            if contract_file.version_root_id is None:
                contract_file.version_root_id = contract_file.id
                db.flush()

            contract_files.append(contract_file)

            # Parse result
            parse_result = ContractParseResult(
                contract_file_id=contract_file.id,
                page_count=1,
                parse_status="completed",
                parse_mode="text",
                raw_text=c["content"],
            )
            db.add(parse_result)
            print(f"  已创建合同 {c['filename']}")

        db.commit()
        print()

        # 4. Run reviews for all contracts
        print("[4/6] 执行合同审查...")
        from app.services.contract_review_service import review_contract_parse_result

        for cf in contract_files:
            # Check if already reviewed
            existing_result = db.query(ContractReviewResult).filter_by(
                contract_file_id=cf.id
            ).first()
            if existing_result:
                print(f"  合同 {cf.original_filename} 已审查，跳过")
                continue

            try:
                review_contract_parse_result(db, cf.id, actor=admin, trigger_source="manual")
                print(f"  已审查 {cf.original_filename}")
            except Exception as e:
                print(f"  审查 {cf.original_filename} 失败: {e}")

        db.commit()
        print()

        # 5. Create some extra review logs
        print("[5/6] 写入额外操作日志...")
        log_entries = [
            ("system_setting", "系统配置", "更新系统设置：审查模式改为 mock"),
            ("user", None, f"创建演示用户 zhang_reviewer"),
            ("user", None, f"创建演示用户 li_viewer"),
        ]
        for target_type, target_id, detail in log_entries:
            db.add(ReviewLog(
                operator_id=admin.id if admin else None,
                target_type=target_type,
                target_id=target_id,
                action_type="edit",
                action_detail=detail,
            ))

        db.commit()
        print("  已写入额外操作日志\n")

        # 6. Summary
        print("[6/6] 完成")
        print(f"\n  用户数: {db.query(User).count()}")
        print(f"  规则数: {db.query(ReviewRule).filter_by(is_deleted=False).count()}")
        print(f"  合同数: {db.query(ContractFile).count()}")
        print(f"  审查结果数: {db.query(ContractReviewResult).count()}")
        print(f"  审查版本数: {db.query(ReviewVersion).count()}")
        print(f"  操作日志数: {db.query(ReviewLog).count()}")
        print(f"\n  演示账号: zhang_reviewer / Reviewer123（reviewer）")
        print(f"  演示账号: li_viewer / Viewer12345（viewer）")
        print(f"  管理员: admin / Admin123456\n")

    except Exception as e:
        db.rollback()
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
