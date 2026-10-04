#!/usr/bin/env python3
"""
Re-export of primus.rca_analysis for backwards compatibility.
The canonical implementation lives in primus/rca_analysis.py.
"""
from primus.rca_analysis import analyze_score_result, build_feedback_context

__all__ = ["analyze_score_result", "build_feedback_context"]
