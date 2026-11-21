PY := .venv/bin/python

# NixOS only: pip wheels need libstdc++/libz (from nix-ld) and libexpat (rasterio).
# On other systems NIX_LD_LIBRARY_PATH is unset and this block does nothing.
ifdef NIX_LD_LIBRARY_PATH
NIX_EXPAT := $(shell nix-build '<nixpkgs>' -A expat --no-out-link 2>/dev/null)
export LD_LIBRARY_PATH := $(NIX_LD_LIBRARY_PATH):$(NIX_EXPAT)/lib:$(LD_LIBRARY_PATH)
endif

.PHONY: setup test grid run

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	$(PY) -m pytest -q

grid:
	$(PY) -m src.grid

run:
	.venv/bin/streamlit run app/main.py
