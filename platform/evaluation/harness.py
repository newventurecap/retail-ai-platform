from collections.abc import Callable, Sequence
from dataclasses import dataclass, field


@dataclass
class Case:
    name: str
    input: str
    context: list[str] = field(default_factory=list)


@dataclass
class Report:
    results: list[dict]

    @property
    def pass_rate(self) -> float:
        return sum(r["passed"] for r in self.results) / len(self.results) if self.results else 1.0

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.results if not r["passed"]]

    def assert_pass(self, threshold: float = 1.0) -> None:
        if self.pass_rate < threshold:
            lines = [f"{r['case']}: {r['reason']}" for r in self.failures]
            raise AssertionError(f"pass rate {self.pass_rate:.0%} < {threshold:.0%}\n" + "\n".join(lines))


def run_eval(agent_fn: Callable[[Case], str], cases: Sequence[Case], checks: Sequence[Callable]) -> Report:
    """Run ``agent_fn`` over cases and apply every check to each output."""
    results = []
    for case in cases:
        output = agent_fn(case)
        for check in checks:
            passed, reason = check(case, output)
            results.append({"case": case.name, "check": getattr(check, "__name__", "check"),
                            "passed": passed, "reason": reason, "output": output})
    return Report(results)
