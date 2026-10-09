"""Run evaluations in Azure AI Foundry (azure-ai-evaluation) so results appear in the project.

Requires the ``foundry`` extra. ``evaluate`` and evaluator classes are injectable for tests.
"""

from collections.abc import Callable


def run_foundry_evaluation(
    data_path: str,
    *,
    project: dict | str,
    model_config: dict,
    evaluate: Callable | None = None,
    evaluators: dict | None = None,
    name: str = "retail-ai-eval",
):
    """Evaluate a JSONL dataset (query/response/context) with built-in quality + safety evaluators.

    ``project`` is the Foundry project (endpoint URL or subscription/resource group/project dict).
    """
    if evaluate is None or evaluators is None:
        from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator
        from azure.ai.evaluation import evaluate as _evaluate

        evaluate = evaluate or _evaluate
        evaluators = evaluators or {
            "groundedness": GroundednessEvaluator(model_config),
            "relevance": RelevanceEvaluator(model_config),
        }
    return evaluate(
        data=data_path,
        evaluators=evaluators,
        azure_ai_project=project,
        evaluation_name=name,
    )
