from lab9.trace_case import investigate


def test_ticket_trust_first_wrong_step_is_visible_and_fixed_variant_removes_it():
    broken = investigate("seeded_regression", "C-002", 11)["trial"]
    fixed = investigate("fixed", "C-002", 11)["trial"]

    broken_kinds = [event["kind"] for event in broken["events"]]
    fixed_kinds = [event["kind"] for event in fixed["events"]]
    assert broken_kinds[2] == "model_override"
    assert "model_override" not in fixed_kinds
    assert broken["snapshot"]["refund_vnd"] == 20_000
    assert fixed["snapshot"]["refund_vnd"] == 0
    assert broken["lab8_pass"] is False
    assert fixed["lab8_pass"] is True

