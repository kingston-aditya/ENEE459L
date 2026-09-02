# Lab 01 — What is this machine, and how do you know?

You have been handed a Jetson Orin Nano Super Developer Kit. Before you measure
anything on it for the rest of the semester, you need to establish what it is
and whether it was set up correctly — and you need to establish it in a form
somebody else can check.

That last clause is the whole lab. Reading numbers off a screen is easy. Producing
a record that a grader, a classmate, or you in eleven weeks can verify without
having the board in front of them is the skill being built.

## The lab question

**Is this unit configured correctly enough that a benchmark run on it will mean
anything — and what is your evidence?**

There is a specific failure this lab is built around. A Jetson can have an NVMe
drive fitted, visible to the kernel, and completely unused, because the unit was
imaged onto the SD card and boots from it. Such a machine works. It passes every
casual inspection. It also runs the semester's benchmarks against storage an
order of magnitude slower than the drive sitting in its slot, and every number
you produce on it will be quietly, unreproducibly wrong.

Nobody notices this by looking at the board. You notice it by running a command
and recording the answer.

## What you hand in

`system_report.json` — not a screenshot, not a paragraph in a lab notebook, not
a photo of the terminal. A JSON file with a fixed shape, which Assignment 1 will
compare across all twenty groups.

Two rules the format enforces, because they are the rules the rest of the course
runs on:

**Every value carries its source.** A finding without a `source` field is
rejected by the validator before a grader ever sees it. `7650000` is a number;
`7650000 kB, from /proc/meminfo` is evidence. The difference matters the moment
somebody disagrees with you.

**Every claim carries its evidence.** A verdict is not a boolean you set by
hand. It is derived from a finding, and it carries that finding with it. This
makes it impossible to submit a report that claims a machine passed a check the
code never ran.

## Setting up

```
python3 tests/make_fixtures.py          # build the fake machines to test against
python3 -m pytest tests/test_public.py -v
```

Everything runs on your laptop. The probes read from a `root` directory you give
them, so the test suite can hand them a fabricated NVMe-booted machine, a
fabricated SD-booted machine, and a machine with almost nothing readable, and
check that your code tells the three apart.

This is not a convenience. Code that hardcodes `/` cannot be tested, and a
measurement nobody can test is a measurement nobody should believe. The tests
check that your probes honour their `root` argument, and you will lose marks if
they do not — on a real board the difference is invisible, which is exactly why
it is worth checking.

## The work

Eight functions in `enee459l/probes.py`, each marked `TODO`: the seven probes in
the table below, plus `_parse_link_line`, the helper the PCIe probe leans on.
Everything else — the report assembly, the schema, the validator, the
command-line interface — is provided complete. Read them anyway; you are
expected to be able to explain what the exit codes mean.

| Probe | Reads | The trap |
|---|---|---|
| `probe_module_model` | `/proc/device-tree/model` | The node is NUL-terminated |
| `probe_memory_total_kb` | `/proc/meminfo` | It is kB, and it is less than 8 GB |
| `probe_root_source` | `/proc/mounts` | Root is not always the first line, and `/var` is not `/` |
| `probe_nvme_present` | `/sys/block/nvme0n1` | Fitted and booted-from are different questions |
| `probe_pcie_link` | `lspci -vv` | Two numbers, not one |
| `probe_thermal_zones` | `/sys/class/thermal/` | Millidegrees |
| `probe_power_mode` | `nvpmodel -q` | Absent off-target, and that is not a crash |

### On the two PCIe numbers

`LnkSta` is what the link actually negotiated. `LnkCap` is what the device was
capable of. On this hardware they will differ: the devkit's M.2 Key-M slot is
wired for PCIe Gen3 x4, so a Gen4 drive advertising 16 GT/s will settle at
8 GT/s.

That is not a fault, and reporting it as one is a worse error than missing it.
It is also not "the drive is Gen3" — the drive is Gen4 and the slot is Gen3, and
those have different consequences if the drive is ever moved. Report both
numbers and say what the gap means. A student who records only the negotiated
speed has written down a fact without writing down what it means.

### On `unknown`

When a probe cannot determine something, it returns `unknown(source, why)` — a
record that the probe ran, failed, and knows why. Never `0`, never `""`, never a
plausible default.

This is graded, and it is graded positively. `unknown` is a correct answer. A
fabricated zero is not, and it is worse than a blank, because a zero goes into a
chart and nobody can tell afterwards that it was invented.

The exit codes make the same distinction:

```
0   every verdict passed
1   a verdict failed          — go fix the machine
2   a verdict is unknown      — go fix your measurement
3   the report failed schema validation — go fix the code
```

`1` and `2` are different problems with different fixes. Collapsing them into
"it didn't work" is how somebody ends up reimaging a perfectly good board whose
only issue was that `pciutils` was not installed.

## Running it for real

On the board:

```
python3 system_report.py --device-id jetson-07 -o system_report.json
```

Use the label on the physical unit for `--device-id`, not the hostname. Hostnames
get changed and reused; the sticker is what lets somebody walk to the right desk.

Some probes need `sudo` to see everything — `lspci -vv` will print `LnkCap` only
when it can read the full config space. Run it both ways and notice what changes.
If you cannot get `LnkCap`, that is an `unknown` with a reason, and it is a
legitimate submission.

## Before you hand in

- `python3 -m pytest tests/test_public.py` passes
- `system_report.json` validates: `python3 -c "import json,sys; from enee459l import schema; print(schema.validate(json.load(open('system_report.json'))) or 'valid')"`
- The report was generated on the board, not on your laptop — check `probe_root`
- Every `unknown` in it has a `detail` saying why
- You can explain, out loud, why the memory reading is under 8 GB and why the
  PCIe link is Gen3

The public tests are not the whole grade. They are the floor: nothing that fails
them can pass anything else. There are additional tests you have not seen, and
they check that your probes work for the right reason rather than by coincidence
— that they read from the root they were given, that they do not return a
plausible default when a read fails, and that they distinguish two machines that
differ only in the way this lab cares about.

## On the day

This document is the half of Lab 01 you do on your laptop, before the session. The
other half happens at the bench, and it has its own handout — `HANDOUT.md`, one
directory up. Read it before you arrive, because two of its stages assume you
already have a working `system_report.py` and there is no time in the session to
write one.

Two things in that handout are worth knowing in advance. You will run `findmnt /`
twice, forty minutes apart, and get two different answers about the same machine;
recording both is the lab's central piece of evidence. And you will not be
assembling the camera — the ribbon is seated and labelled before you arrive, and
it stays that way.

## Next

Lab 01 established what the machine is. Lab 02 establishes what is installed on
it — a harder question, because software can be wrong and still work: a board
with the wrong PyTorch wheel runs your code, prints a plausible version number,
and silently uses the CPU. Lab 03 then measures the machine, and the benchmark
record it produces has the same two rules as this report: every value carries
its source, every claim carries its evidence. This report is the smallest
version of that artifact, which is why it comes first.
