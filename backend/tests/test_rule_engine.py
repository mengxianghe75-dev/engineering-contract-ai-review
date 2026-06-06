"""
工程合同 AI 审查助手 — 后端测试

运行方式：
    cd backend
    pip install -r requirements-dev.txt
    pytest

当前覆盖范围：
- 规则引擎匹配逻辑
- 风险合并去重
- 合同字段提取（正则）
"""

import pytest
from unittest.mock import MagicMock

from app.services.rule_engine_service import (
    _parse_scope,
    _scope_matches,
    _match_rule,
)
from app.services.contract_review_service import (
    _clean_value,
    merge_review_risks,
)
from app.schemas.review import ContractExtractedFields, ReviewRiskItem, ReviewMatchDetail


# --- 规则引擎测试 ---

class TestParseScope:
    def test_empty_scope(self):
        assert _parse_scope(None) == []
        assert _parse_scope("") == []

    def test_json_scope(self):
        result = _parse_scope('["施工合同", "分包合同"]')
        assert result == ["施工合同", "分包合同"]

    def test_csv_scope(self):
        result = _parse_scope("施工合同, 分包合同")
        assert result == ["施工合同", "分包合同"]


class TestScopeMatches:
    def test_no_scope_matches_all(self):
        rule = MagicMock(contract_type_scope=None)
        fields = ContractExtractedFields(contract_type="施工合同")
        assert _scope_matches(rule, fields) is True

    def test_matching_scope(self):
        rule = MagicMock(contract_type_scope='["施工合同", "分包合同"]')
        fields = ContractExtractedFields(contract_type="施工合同")
        assert _scope_matches(rule, fields) is True

    def test_non_matching_scope(self):
        rule = MagicMock(contract_type_scope='["采购合同"]')
        fields = ContractExtractedFields(contract_type="施工合同")
        assert _scope_matches(rule, fields) is False


class TestMatchRule:
    def test_keyword_match(self):
        rule = MagicMock(condition_type="keyword", condition_value="预付款")
        assert _match_rule(rule, "本合同无预付款，竣工后支付") is not None

    def test_keyword_no_match(self):
        rule = MagicMock(condition_type="keyword", condition_value="预付款")
        assert _match_rule(rule, "按月进度支付工程款") is None

    def test_contains_any_match(self):
        rule = MagicMock(condition_type="contains_any", condition_value='["甲方", "乙方"]')
        assert _match_rule(rule, "甲方与乙方签订合同") is not None

    def test_contains_all_match(self):
        rule = MagicMock(condition_type="contains_all", condition_value='["甲方", "乙方"]')
        assert _match_rule(rule, "甲方与乙方签订合同") is not None

    def test_contains_all_partial(self):
        rule = MagicMock(condition_type="contains_all", condition_value='["甲方", "丙方"]')
        assert _match_rule(rule, "甲方与乙方签订合同") is None

    def test_regex_match(self):
        rule = MagicMock(condition_type="regex", condition_value=r"\d{4}年\d{1,2}月")
        result = _match_rule(rule, "签订日期：2026年4月1日")
        assert result is not None


# --- 合同审查服务测试 ---

class TestCleanValue:
    def test_clean_whitespace(self):
        assert _clean_value("  合同名称  ：   某工程合同  ") == "合同名称  ： 某工程合同"

    def test_clean_punctuation(self):
        assert _clean_value("value：") == "value"
        assert _clean_value(":value:") == "value"


class TestMergeReviewRisks:
    def _make_risk(self, code, title, source="rule"):
        return ReviewRiskItem(
            code=code,
            title=title,
            level="high",
            description="test",
            recommendation="test",
            source=source,
            match_detail=ReviewMatchDetail(
                condition_type="keyword",
                condition_value=title,
                text_span=title,
            ),
        )

    def test_no_duplicates(self):
        rule_risks = [self._make_risk("payment", "付款风险", "rule")]
        ai_risks = [self._make_risk("payment", "付款风险", "ai")]
        merged = merge_review_risks(rule_risks, ai_risks)
        assert len(merged) == 1
        assert merged[0].source == "rule"

    def test_different_codes(self):
        rule_risks = [self._make_risk("payment", "付款风险", "rule")]
        ai_risks = [self._make_risk("settlement", "结算风险", "ai")]
        merged = merge_review_risks(rule_risks, ai_risks)
        assert len(merged) == 2

    def test_empty_lists(self):
        assert merge_review_risks([], []) == []
