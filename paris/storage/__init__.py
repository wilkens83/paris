"""Persistence layer (plan sections 18-20).

    from paris.storage import AnalysisStore
    with AnalysisStore("paris.db") as store:
        store.save(analysis, event)
"""

from .sqlite import AnalysisStore, ERROR_CATEGORIES, new_analysis_id

__all__ = ["AnalysisStore", "ERROR_CATEGORIES", "new_analysis_id"]
