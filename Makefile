# Tonalis — dev convenience targets.

.PHONY: fuzz fuzz-seed2

# Run the 3-way Python↔TS↔Rust differential fuzzer (seed=1, N=500).
# 0 divergences required to exit 0. Add SEED=N to change seed.
fuzz:
	@bash conformance/music-dsl/fuzz/run_fuzz.sh $(SEED) $(N)

# Convenience: run the fuzzer with seed=2 to cross-validate.
fuzz-seed2:
	@bash conformance/music-dsl/fuzz/run_fuzz.sh 2 500
