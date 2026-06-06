export const roleLabelMap = {
  admin: "管理员",
  reviewer: "审查员",
  viewer: "只读用户",
};

export const contractStatusLabelMap = {
  uploaded: "已上传",
  parsed: "已解析",
  reviewed: "已审查",
  archived: "已归档",
};

export const riskLevelLabelMap = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

export const conditionTypeLabelMap = {
  keyword: "关键词",
  regex: "正则表达式",
  contains_any: "命中任一",
  contains_all: "命中全部",
};

export const providerLabelMap = {
  mock: "模拟模式",
  openai_compatible: "OpenAI 兼容模式",
  mixed_rule_llm: "规则优先 + 大模型补充",
  mock_fallback: "降级到模拟模式",
  not_reviewed: "未审查",
};

export const triggerSourceLabelMap = {
  manual: "手动触发",
  auto: "自动触发",
  auto_after_ocr: "OCR 后自动触发",
  not_reviewed: "尚未审查",
};

export const targetTypeLabelMap = {
  contract: "合同",
  rule: "规则",
  user: "用户",
  system_setting: "系统设置",
};

export function roleLabel(value) {
  return roleLabelMap[value] || value || "-";
}

export function contractStatusLabel(value) {
  return contractStatusLabelMap[value] || value || "-";
}

export function riskLevelLabel(value) {
  return riskLevelLabelMap[value] || value || "-";
}

export function conditionTypeLabel(value) {
  return conditionTypeLabelMap[value] || value || "-";
}

export function providerLabel(value) {
  return providerLabelMap[value] || value || "-";
}

export function triggerSourceLabel(value) {
  return triggerSourceLabelMap[value] || value || "-";
}

export function targetTypeLabel(value) {
  return targetTypeLabelMap[value] || value || "-";
}
