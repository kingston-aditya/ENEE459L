#!/usr/bin/env bash
# The Lab 01 release gate.
#
#     bash verify_all.sh
#
# A wrapper, kept because this path is cited in INSTRUCTOR.md and in docs/.
# The gate itself is instructor/labkit/gate.py and what it checks for this lab
# is declared in labconfig.py. It was moved out of this file when Lab 02 was
# written: three tooling files copied per lab, times fifteen labs, is forty-five
# files that drift apart silently, and the drift is not visible until a starter
# ships with an answer in it.
#
# Equivalent, and the form to prefer:
#
#     python3 -m labkit gate labs/lab01     # from instructor/, or with it on PYTHONPATH
#     python3 -m labkit gate labs/*         # every lab, one summary

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec env PYTHONPATH="$HERE/../../instructor${PYTHONPATH:+:$PYTHONPATH}" \
     python3 -m labkit gate "$HERE"
