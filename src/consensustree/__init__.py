"""ConsensusTree AI public SDK."""
from .core import Council, CouncilReport, ModelSpec
from .hierarchy import HierarchicalCouncil, adaptive_group_count

__all__ = ["Council", "CouncilReport", "ModelSpec", "HierarchicalCouncil", "adaptive_group_count"]
__version__ = "6.3.0rc1"
