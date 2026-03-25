"""Compatibility entrypoint for ontology evaluation.

This module forwards to the newer two-track evaluator implementation while preserving
existing script path usage:

    python evaluate/evaluate_ontology_compliance.py ...
"""

try:
    from .two_track_evaluation import evaluate, main
except ImportError:
    from two_track_evaluation import evaluate, main


if __name__ == "__main__":
    main()
