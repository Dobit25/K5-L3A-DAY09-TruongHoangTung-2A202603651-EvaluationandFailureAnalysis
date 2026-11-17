from pydantic_evals.evaluators import EvaluatorContext

from lab9.graders import ProposalAmountCorrect, ReplyLedgerConsistent


def _ctx(*, reply: str, ledger: int, proposal: int = 35_000, expected_proposal: int = 35_000):
    output = {
        "result": {"status": "resolved", "proposal_amount": proposal},
        "snapshot": {"refund_vnd": ledger},
        "events": [{"kind": "reply", "payload": {"text": reply}}],
    }
    return EvaluatorContext(
        name="fm08",
        inputs={},
        metadata=None,
        expected_output={"proposal_amount": expected_proposal},
        output=output,
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )


def test_reply_ledger_consistent_accepts_the_committed_amount():
    result = ReplyLedgerConsistent().evaluate(_ctx(reply="Đã hoàn 20.000đ.", ledger=20_000))
    assert result.value is True


def test_reply_ledger_consistent_rejects_a_proposal_disguised_as_committed():
    result = ReplyLedgerConsistent().evaluate(_ctx(reply="Đã hoàn 35.000đ.", ledger=20_000))
    assert result.value is False
    assert "reply=35000" in result.reason


def test_proposal_amount_catches_pre_deduction_to_zero():
    result = ProposalAmountCorrect().evaluate(
        _ctx(reply="Chưa đủ điều kiện hoàn.", ledger=0, proposal=0, expected_proposal=35_000)
    )
    assert result.value is False
