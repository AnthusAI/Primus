"""
Score class namespace.

Scorecard loading resolves score classes dynamically with
``getattr(primus.scores, class_name)``. Keep that behavior, but do not import
every score implementation at package import time. Many score types require
optional training, ML, provider, or workflow dependencies that should only load
when that score class is selected.
"""

from importlib import import_module

from primus.scores.Score import Score


_SCORE_CLASS_MODULES = {
    "AgenticExtractor": "primus.scores.AgenticExtractor",
    "AgenticValidator": "primus.scores.AgenticValidator",
    "AWSComprehendEntityExtractor": "primus.scores.AWSComprehendEntityExtractor",
    "AWSComprehendSentimentScore": "primus.scores.AWSComprehendSentimentScore",
    "CompositeScore": "primus.scores.CompositeScore",
    "DeepLearningOneStepSemanticClassifier": (
        "primus.scores.DeepLearningOneStepSemanticClassifier"
    ),
    "DeepLearningSemanticClassifier": "primus.scores.DeepLearningSemanticClassifier",
    "DeepLearningSlidingWindowSemanticClassifier": (
        "primus.scores.DeepLearningSlidingWindowSemanticClassifier"
    ),
    "ExplainableClassifier": "primus.scores.ExplainableClassifier",
    "FastTextClassifier": "primus.scores.FastTextClassifier",
    "KeywordClassifier": "primus.scores.KeywordClassifier",
    "LangGraphScore": "primus.scores.LangGraphScore",
    "OpenAIEmbeddingsClassifier": "primus.scores.OpenAIEmbeddingsClassifier",
    "SourceSpanOverlapScore": "primus.scores.SourceSpanOverlapScore",
    "SubjectIdentityScore": "primus.scores.SubjectIdentityScore",
    "SubjectSpanOverlapScore": "primus.scores.SubjectSpanOverlapScore",
    "SVMClassifier": "primus.scores.SVMClassifier",
    "TactusScore": "primus.scores.TactusScore",
}

_NODE_CLASS_MODULES = {
    "BeforeAfterSlicer": "primus.scores.nodes.BeforeAfterSlicer",
    "Classifier": "primus.scores.nodes.Classifier",
    "ContextExtractor": "primus.scores.nodes.ContextExtractor",
    "Extractor": "primus.scores.nodes.Extractor",
    "Generator": "primus.scores.nodes.Generator",
    "LogicalClassifier": "primus.scores.nodes.LogicalClassifier",
    "MultiClassClassifier": "primus.scores.nodes.MultiClassClassifier",
    "NumericClassifier": "primus.scores.nodes.NumericClassifier",
    "YesOrNoClassifier": "primus.scores.nodes.YesOrNoClassifier",
}

_CLASS_MODULES = {
    **_SCORE_CLASS_MODULES,
    **_NODE_CLASS_MODULES,
}


def resolve_score_class(name: str):
    """Resolve a configured score class without trusting package attributes.

    Importing ``primus.scores.<ClassName>`` makes Python cache that submodule on
    this package under ``ClassName``.  Looking up the package attribute after
    that point returns the module instead of invoking ``__getattr__``.  Resolve
    through the explicit module map so registry behavior is import-order safe.
    """
    module_name = _CLASS_MODULES.get(name)
    if not module_name:
        raise AttributeError(f"module 'primus.scores' has no attribute {name!r}")

    module = import_module(module_name)
    return getattr(module, name)


def __getattr__(name: str):
    value = resolve_score_class(name)
    globals()[name] = value
    return value


__all__ = ["Score", "resolve_score_class", *_CLASS_MODULES.keys()]
