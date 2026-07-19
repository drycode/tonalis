from dataclasses import dataclass

from music_dsl.domain.static.notes import Notes
from music_dsl.encode import Scales


@dataclass
class Key:
    root: Notes
    scale: Scales


__version__ = "0.1.0"

# The thin top-level surface (Key/Notes/Scales) is intentional: deeper theory is
# submodule-scoped (see API-SURFACE.md). __all__ keeps `import *` to exactly this.
__all__ = ["Key", "Notes", "Scales", "__version__"]
