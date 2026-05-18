#!/bin/bash
# SigmaFidelity™ Institutional Search Engine
# Standard: HWB-QMS-9.2 (Knowledge Management)

KEYWORDS=$1
echo "--- SigmaFidelity™: Searching Knowledge Base for '$KEYWORDS' ---"
grep -ri "$KEYWORDS" docs/solutions/
