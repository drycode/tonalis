"""One-shot: (re)generate the scale conformance cases from the frozen Python reference.

Run: .venv/bin/python conformance/music-dsl/runners/python/bless_scales.py
Writes:
  cases/encode/scales.json              scale_value (mask) for every scale
  cases/encode/scale_membership.json    scale_contains, pinning the membership algorithm
  cases/transactions/scale_refusal.json is_diatonic refusal on non-functional scales

The mask fully determines membership, so scale_value is the core cross-port contract;
the scale_contains sample pins the shared contains() algorithm; the refusal cases pin
the two-tier model. Ports implement to these blessed values.
"""
import json
from pathlib import Path

from music_dsl.encode import Scales, contains

CASES = Path(__file__).resolve().parents[2] / "cases"

# scale_value for every scale (the mask contract).
scales = [
    {"name": f"scale-{s.name}", "op": "scale_value", "args": {"name": s.name},
     "expect": {"value": s.value.mask}}
    for s in Scales
]

# scale_contains across representative scales, all 12 pitch classes — pins the
# algorithm over a functional heptatonic, a symmetric hexatonic, an octatonic,
# and the all-set chromatic.
membership = []
for name in ["Major", "WholeTone", "DiminishedHalfWhole", "Chromatic"]:
    for pc in range(12):
        membership.append(
            {"name": f"contains-{name}-{pc}", "op": "scale_contains",
             "args": {"name": name, "pitch_class": pc},
             "expect": {"value": contains(Scales[name], pc)}}
        )

# is_diatonic must refuse on every non-functional scale (two-tier model).
refusal = [
    {"name": f"refuse-{s.name}", "op": "is_diatonic",
     "args": {"root": "C", "scale": s.name, "chord": "C"}, "expect": {"error": True}}
    for s in Scales if not s.value.supports_diatonic_function
]

(CASES / "encode" / "scales.json").write_text(json.dumps(scales, indent=2) + "\n")
(CASES / "encode" / "scale_membership.json").write_text(json.dumps(membership, indent=2) + "\n")
(CASES / "transactions" / "scale_refusal.json").write_text(json.dumps(refusal, indent=2) + "\n")

print(f"blessed: {len(scales)} scale_value, {len(membership)} scale_contains, {len(refusal)} refusal")
print(f"new case total delta: +{len(scales) - 3 + len(membership) + len(refusal)}")
