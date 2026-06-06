from app.schemas.review import ContractExtractedFields, ReviewRiskItem


def build_mock_summary(
    fields: ContractExtractedFields,
    risks: list[ReviewRiskItem],
) -> str:
    name = fields.contract_name or fields.project_name or "该合同"
    if risks:
        top_risks = "、".join(risk.title for risk in risks[:3])
        return f"{name} 已完成规则审查，共识别 {len(risks)} 项风险，重点包括：{top_risks}。建议优先核对付款、工期与违约责任条款。"

    return f"{name} 已完成规则审查，当前未发现明显高风险条款。建议结合业务背景复核关键商务条件。"
