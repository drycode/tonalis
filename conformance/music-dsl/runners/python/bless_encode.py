"""One-shot: print blessed conformance/music-dsl/cases/encode/*.json from the frozen Python reference.
Run: python conformance/music-dsl/runners/python/bless_encode.py  -> paste each block into its file.
The encode bit-layout IS the contract, so expected values are whatever the reference computes (blessed)."""
import json
from music_dsl.encode import Encoding, Scales, EncodingMap
from music_dsl.domain.static import Notes, Triad, Seventh, Extensions
from music_dsl.helpers import strip_left, strip_right, semitones_apart_ascending

def enc(triad, seventh, exts):
    return Encoding(root=Notes.C, triad=Triad[triad], _7th=Seventh[seventh],
                    extensions=[Extensions[e] for e in exts]).value

scales = [{"name": f"scale-{n}", "op": "scale_value", "args": {"name": n},
           "expect": {"value": Scales[n].value}} for n in ["Major","Minor","HarmonicMinor"]]

# cover every triad x {None,Minor,Major} 7th, plus representative extensions and the alt set.
enc_cases = []
triads = ["Major","Minor","Diminished","HalfDiminished","Augmented","Sus2","Sus","Sus4"]
for t in triads:
    for s in ["_None","Minor","Major"]:
        enc_cases.append({"name": f"enc-{t}-{s}", "op": "encoding_value",
                          "args": {"triad": t, "seventh": s, "extensions": []},
                          "expect": {"value": enc(t, s, [])}})
for exts in [["b9"],["add9"],["s9"],["add11"],["s11"],["b13"],["add13"],["add6"],["b5"],["s5"],["alt"]]:
    enc_cases.append({"name": f"enc-Major-Minor-{'-'.join(exts)}", "op": "encoding_value",
                      "args": {"triad": "Major", "seventh": "Minor", "extensions": exts},
                      "expect": {"value": enc("Major","Minor",exts)}})

strip = []
for bits, x in [(46534580949, 0),(46534580949, 5),(46534580949, 12),(262144, 7),(299520, 7)]:
    try: v = strip_left(bits, x); strip.append({"name": f"sl-{bits}-{x}", "op": "strip_left","args":{"bits":bits,"x":x},"expect":{"value":v}})
    except Exception: strip.append({"name": f"sl-{bits}-{x}-err", "op":"strip_left","args":{"bits":bits,"x":x},"expect":{"error":True}})
for bits, x in [(280832, 7),(299520, 7),(262144, 0)]:
    try: v = strip_right(bits, x); strip.append({"name": f"sr-{bits}-{x}", "op": "strip_right","args":{"bits":bits,"x":x},"expect":{"value":v}})
    except Exception: strip.append({"name": f"sr-{bits}-{x}-err","op":"strip_right","args":{"bits":bits,"x":x},"expect":{"error":True}})

semis = [{"name": f"sa-{r}-{n}", "op": "semitones_apart_ascending", "args": {"root": r, "note": n},
          "expect": {"value": semitones_apart_ascending(Notes(r), Notes(n))}}
         for r, n in [("C","G"),("C","F"),("G","C"),("E","C"),("C","C"),("Bb","D")]]

for fname, data in [("scales", scales),("encoding", enc_cases),("strip", strip),
                    ("semitones", semis)]:
    print(f"===== cases/encode/{fname}.json =====")
    print(json.dumps(data, indent=2))
