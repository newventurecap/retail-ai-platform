import pytest
from retail_ai.evaluation import (
    Case,
    contains,
    grounded,
    no_pii,
    no_prompt_injection_leak,
    run_eval,
)

POLICY = ["Items may be returned within 30 days with a receipt."]


def good_agent(case):
    return "You may return items within 30 days with a receipt."


def test_good_agent_passes_all_checks():
    cases = [Case("return window", "can I return?", POLICY)]
    report = run_eval(good_agent, cases,
                      [contains("30 days"), grounded(), no_pii, no_prompt_injection_leak()])
    report.assert_pass()


def test_regressions_are_caught():
    cases = [Case("c", "q", POLICY)]
    bad = {
        "pii": lambda c: "Contact jane@example.com or 4111 1111 1111 1111",
        "leak": lambda c: "My SYSTEM PROMPT says...",
        "hallucination": lambda c: "Refunds are issued instantly in cryptocurrency always",
        "missing": lambda c: "No idea",
    }
    checks = {"pii": no_pii, "leak": no_prompt_injection_leak(), "hallucination": grounded(),
              "missing": contains("30 days")}
    for name, agent in bad.items():
        with pytest.raises(AssertionError):
            run_eval(agent, cases, [checks[name]]).assert_pass()


def test_threshold():
    cases = [Case("a", "q"), Case("b", "q")]
    report = run_eval(lambda c: "ok" if c.name == "a" else "bad", cases, [contains("ok")])
    assert report.pass_rate == 0.5
    report.assert_pass(threshold=0.5)
