"""ENEE459L Lab 01 support package.

Three modules, and the split between them is the lesson:

    probes.py   reads the machine and reports what it found, or why it could not
    report.py   assembles findings into verdicts, deriving nothing it was not told
    schema.py   states the shape a report must have, and checks it

Nothing in `probes` decides whether a machine is good; nothing in `report`
reads a file. Keeping those apart is what makes the probes testable against a
fake machine tree, which is what makes this lab gradeable without twenty
Jetsons on a bench.
"""

__all__ = ["probes", "report", "schema"]
