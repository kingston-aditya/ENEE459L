# Lab 01 — Bench Handout

**Platform bring-up and reproducible boot · 110 minutes · one student, one board**

> **DRAFT — DO NOT ISSUE.** Every command in this handout was written from documentation and none
> has been run on a Jetson. It becomes a student document only after the Phase 2 dry run in
> `docs/10_bringup_procedure.md` has been walked end to end and the open items in that document's
> §11 have been closed. Sections marked ⚠ are the ones most likely to change.

---

## The question

**What is actually inside this machine, and how do you prove it?**

You will be handed a Jetson Orin Nano Super Developer Kit that is yours for the
rest of the semester. Every number you produce on it for the next fourteen weeks depends on it being
set up correctly. Today you set it up, and — this is the part that matters — you produce evidence
that it is set up correctly, in a form somebody who is not in this room can check.

The rule the course runs on, stated once here and assumed everywhere after: **distrust any claim
about this system that does not arrive with the command that verifies it.**

## What you will have built by the end of the session

A unit that boots from its NVMe drive rather than from the SD card. A record of the commands that
prove it. A thermal and link-speed baseline for your specific board. And one paragraph about
something that surprised you.

## What you hand in

| Artifact | What it is |
|---|---|
| `system_report.json` | The machine-readable health report. Generated, not typed |
| Boot log | `journalctl -b` from the first NVMe boot, saved to a file |
| `lsblk` and `findmnt` output | **Before and after** the migration. Both. The difference is the point |
| Assembly photographs | Taken as you go, not reconstructed at the end |
| One paragraph | A result you did not expect, and why you think it happened |

---

## Before you touch anything

### Your bench

Check that you have all of it before you start, because discovering a missing screw at minute
seventy is expensive.

| Item | Notes |
|---|---|
| Jetson Orin Nano Super devkit | Heatsink and fan already mounted. Leave them |
| 256 GB NVMe SSD, in its packet | You install this |
| Camera, already connected | **Do not touch the ribbon.** See below |
| microSD card, in the slot | Already imaged. Do not remove it |
| 19 V power supply | Not connected yet |
| DP-to-HDMI cable | One direction only. See below |
| Keyboard and mouse | |
| Monitor | Shared — check the input it is on |
| One M.2 screw | The only one. Do not drop it |

### Three handling rules

**Do not touch the camera ribbon.** It is already seated at both ends and labelled. The flexible
ribbon connecting the camera to the board delaminates if it is inserted and removed repeatedly, and
when it does it fails *silently* — the camera still enumerates, and then returns black frames in
Lab 07, six weeks from now, by which time nobody will connect the two events. We hold one ribbon
per bench and cannot buy more locally. No lab this semester requires the camera to be detached.

**Ground yourself before touching the carrier board.** The M.2 slot and the camera connector are the
two places where a careless second does permanent damage.

**The display cable runs one way.** DisplayPort out of the Jetson, HDMI into the monitor. It is
physically unidirectional — the specification panel on the cable says so — so it will not drive a
monitor from your laptop, and it is not broken when it fails to.

### You are on your own board, and nobody is taking notes for you

This unit is yours for the semester. You open it, you bring it up, you break it, you fix it, and
every report you file in this course comes off it.

There is nobody beside you writing down what you typed. That sounds like a small thing and it is
not, because the single most common way a bring-up log becomes worthless is that it was written from
memory twenty minutes after the fact. **Run every command inside a shell whose output you are
keeping** — `script ~/lab01.log` at the start of the session is enough, and `tee` on anything
important — so that the record exists whether or not you remembered to make it.

The discipline this course assesses is not note-taking. It is that every claim you make about this
machine has a command sitting behind it that someone else can run. Working alone makes that harder
to fake and easier to forget, in that order.

---

## What you are actually testing

Three claims about this machine are printed on a box somewhere. Today you check them against the
machine.

**Claim: it has an NVMe drive, so it runs on NVMe.** A Jetson can have a drive fitted, visible to
the kernel, correctly partitioned, and completely unused, because the operating system was imaged
onto the SD card and boots from it. Such a unit works. It passes every casual inspection. It also
runs the semester's benchmarks against the card rather than against the drive sitting unused in its
slot, and every number it produces is quietly, unreproducibly wrong. Nobody notices this by looking
at the board. You notice it by running one command.

**Claim: the drive is Gen4, so the link is Gen4.** The drive's box says Gen4. The carrier board's
documentation says the slot is wired Gen3. Only the machine can tell you what the two of them
actually agreed on, and Stage E is where you ask it.

**Claim: the specification says the module has this much memory and these many cores.** Probably
true. Prove it anyway, from the machine, and record where you read it from.

---

## Stage A — Inspect and install the drive · 15 min

**A1.** Photograph the bench before you change anything. Everything laid out, one frame. This is
your first artifact and you cannot take it later.

**A2.** Confirm the heatsink sits flat on the module and the fan cable reaches its header without
tension. Do not remove either. Photograph it.

**A3.** Confirm the camera ribbon label is intact at both ends. If it is not, or if the ribbon looks
creased or lifted at a connector, stop and tell an instructor. Do not fix it yourself.

**A4.** Install the NVMe drive. Read `common/media/diagrams/m2_nvme_install.svg` first — it is a
scale drawing of this board's underside and it is quicker than this paragraph.

Turn the unit over so the 40-pin header is nearest you. **There are two M.2 Key-M slots along the
far edge, not one.** They look identical. They are told apart by the little brass standoff that the
retention screw goes into: the left-hand slot's standoff is 30 mm from the connector, the
right-hand slot's is 80 mm. Your drive is an 80 mm module — a 2280 — so it goes in the
**right-hand** slot, the one with the far standoff.

Offer the drive in at roughly 20–30°, push it home with light pressure — if it needs force, it is
not aligned — then press the far end flat and fit the single screw. Snug, then stop.

> ⚠ **If it will not lie flat, you are in the wrong slot.** A 2280 started in the left-hand slot
> reaches right over the Wi-Fi module in the Key-E slot and lands on top of it, with nothing
> underneath to screw into. Do not press it down. Back it out and move it one slot right.

Do not touch the Key-E slot or the two thin antenna leads clipped to it.

Photograph the drive half-inserted, then seated and screwed. Same angle, two frames.

**A5.** Connect display, keyboard and mouse. Power last.

> ⚠ **Open:** whether this carrier requires a jumper to select barrel-jack power is not yet
> confirmed. Check `docs/10_bringup_procedure.md` §5.5 before the session.

---

## Stage B — First boot and identity · 15 min

**B1.** Power on. The unit boots from the microSD card, which has been imaged for you.

**B2.** Work through the Ubuntu OEM setup: licence, language, keyboard, timezone, then your
username and password. **Set the hostname to your assigned unit label** — the one physically on the
chassis, `jetson-XX`. That hostname is how you will reach this board over the network for the rest
of the semester, and it must match the label.

Set the APP partition to the largest size offered. When asked for a power mode, take the highest one
listed.

**B3.** Open a terminal. Verify the power mode from the shell rather than trusting the installer,
and read the mode by **name**, not by index — the index numbers move between JetPack releases:

```bash
sudo nvpmodel -q --verbose      # what modes does this unit have?
sudo nvpmodel -q                # which one is it in?
```

If it is not in MAXN SUPER, set it by the index you just read out of the verbose listing, then pin
the clocks:

```bash
sudo nvpmodel -m <index>
sudo jetson_clocks
```

**B4.** Ask the machine what it is. Save every one of these outputs *now*, into your log, not from
memory afterwards:

```bash
cat /proc/device-tree/model
head -1 /etc/nv_tegra_release
free -h
grep MemTotal /proc/meminfo
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT
findmnt /
```

**✔ Checkpoint B.** Look at what `findmnt /` just told you. The `SOURCE` column names an `mmcblk`
device — the SD card. Your NVMe drive is in `lsblk` and is not mounted anywhere.

Write down the exact `SOURCE` string. You are going to run this identical command again in forty
minutes and get a different answer, and those two answers together are the most important evidence
you produce today.

---

## Stage C — Move the root filesystem to NVMe · 25 min ⚠

> ⚠ **This stage is unverified.** The method below is the intended one and may change after the
> Phase 2 dry run. See `docs/10_bringup_procedure.md` §8 — including a scripted alternative and
> three questions that must be answered on real hardware first.

Right now the drive you installed is doing nothing. The operating system lives on the card, so every
disk-bound step this semester — engine builds, dataset loads, model checkpoints — goes through the
card and not through the drive. How much that costs on this board is not a number anyone has handed
you and not a number this handout will assert. It is measurable. If you want it, measure it before
you migrate and again afterwards, and you will have something better than an assertion.

You are going to copy the root filesystem onto the NVMe and then tell the boot chain to use it.
Three things happen, in order, and it is worth knowing which is which:

1. **Prepare the destination.** Partition and format the NVMe.
2. **Copy.** `rsync` the running root filesystem onto it, preserving everything that matters —
   permissions, ownership, hard links, extended attributes, ACLs — and not crossing into other
   filesystems.
3. **Redirect the boot chain.** Change the `root=` argument the bootloader hands the kernel so that
   it points at the new partition's PARTUUID instead of the card's.

Then reboot, and ask the same question you asked in Checkpoint B.

**The microSD card stays in the slot.** The root filesystem moves; the boot chain does not. This is
worth pausing on, because it is a distinction most people never have to make: "where the system
boots from" and "where the system lives" are two different questions with two different answers, and
today they have two different answers on your bench.

**If it goes wrong:** a wrong PARTUUID drops you to an initramfs prompt rather than a login screen.
This is recoverable and an instructor will walk you back. It is not a disaster and it is not
unusual — read the error, it names the device it could not find.

**✔ Checkpoint C.** Reboot, then:

```bash
findmnt /
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT
```

`findmnt /` now names an `nvme` device. Same command, same machine, different answer.

Save both outputs. **Stand up for two minutes here.** Everything after this point
is verification, and the mistakes Stage D punishes are made by people who have been
at one terminal for an hour.

---

## Stage D — Verification and evidence · 15 min

**D1.** Save the boot log from this boot — the first one that came up on NVMe:

```bash
journalctl -b > boot_nvme.log
```

**D2.** Read the thermal zones. The unit has been idle-ish since reboot, so this is your idle
baseline, and it is *your board's* baseline, not the class's:

```bash
for z in /sys/devices/virtual/thermal/thermal_zone*; do
  printf '%s\t%s\n' "$(cat $z/type)" "$(cat $z/temp)"
done
```

The values are in millidegrees Celsius. Record every zone, not just the highest one.

**D3.** Watch the live telemetry for thirty seconds and then stop it:

```bash
sudo tegrastats
```

You are not measuring anything with this yet. You are learning that the board reports GPU
utilisation, memory, thermals and power rails continuously, because from Lab 03 onward these are
your instruments.

**D4.** Generate the health report:

```bash
python3 system_report.py --device-id jetson-XX -o system_report.json
```

This is the program you wrote on your laptop before the session. It exits 0, 1, 2 or 3, and the
exit code means something — if you cannot say what, re-read `README.md` before you hand in.

Open the JSON and check that every value carries a `source`. A finding without one is rejected by
the validator before a grader sees it. `7650000` is a number; `7650000 kB, from /proc/meminfo` is
evidence.

---

## Stage E — Spec sheet against link speed · 10 min

The drive you installed is a Gen4 device. The slot you installed it in — the right-hand one — is
wired Gen3 ×4. Nothing about installing it told you that, and nothing about how the machine behaves
will tell you either.

```bash
sudo lspci -vv | grep -E 'LnkCap|LnkSta'
```

Two lines. `LnkCap` is what the link is capable of. `LnkSta` is what it actually negotiated when the
machine came up. Read the speed and the width out of each.

**Record both, exactly as printed.** Do not round them, do not summarise them, and do not write down
the number on the drive's box instead — the box number is the claim you are testing.

There are two things to find here, not one. The **speed** is the headline: a Gen4 drive in a Gen3
slot. The **width** is quieter and it checks your own work in Stage A. The right-hand slot is wired
×4 and the left-hand one ×2, so if your `LnkSta` reports `Width x2` you did not put the drive where
you think you put it. Say so in your report rather than fixing it silently; a wrong number you
noticed is worth more than a right number you assumed.

The gap between those two lines is the lesson of this lab, and it generalises well past storage:
a component's specification is an upper bound on a component, not a statement about your system.
The system is what the two of them negotiated.

> Class result for our fleet: ⟨MEASURED: nvme_lnksta⟩ negotiated, against a capability of
> ⟨MEASURED: nvme_lnkcap⟩. This is filled in from measured data, not from a datasheet. If it is
> still showing as a token when you read this, nobody has measured it yet — including you, in about
> four minutes.

---

## When it goes wrong

| Symptom | First thing to check |
|---|---|
| No display at all | Monitor input source. Then the cable direction — DP end in the Jetson |
| Boots, but `lsblk` shows no `nvme` device | The drive is not seated. Power down before touching it |
| `findmnt /` still shows `mmcblk` after Stage C | The boot chain was not redirected. The copy probably succeeded; the `root=` edit did not |
| Dropped to an initramfs prompt after reboot | Wrong PARTUUID. Read the error — it names what it could not find. Get an instructor |
| `nvpmodel` has no MAXN SUPER mode | Not your problem to fix. Flag it — the unit's image is wrong |
| Half your commands report nothing useful | You are not running them with `sudo`. A skipped check is not a passed check |
| Camera ribbon looks lifted or creased | Stop. Do not re-seat it. Get an instructor |

**On `sudo`:** several checks need elevation and record as SKIP without it. A SKIP is not evidence
of anything, least of all of a pass. If your report is full of them, it is not a report.

---

## Checkpoint and submission · 10 min

Find a neighbour. Put your two `system_report.json` files side by side and **find one field where
your two units disagree.**

Their report is not part of your hand-in and your grade does not depend on it. It is a control: on
your own you cannot tell whether a number is a fact about the Orin Nano or a fact about your
particular board on your particular bench, and one comparison settles it in a minute.

There will be one. Identical hardware does not produce identical numbers — idle temperature differs
with airflow and where the bench sits, link negotiation can differ, memory availability differs with
what is running. Finding out why is the exercise, not a defect in it.

Write one paragraph: which field disagreed, what your two units reported, and what you think
explains it. If you do not know, say what you would measure next to find out. "I do not know, and
here is how I would check" is a complete answer in this course. A confident guess with no command
behind it is not.

Submit before you leave: `system_report.json`, `boot_nvme.log`, your before-and-after `findmnt` and
`lsblk` outputs, your assembly photographs, and the paragraph.

Power down cleanly before you go — `sudo shutdown -h now`, then wait for it to actually stop.
Pulling power from a running Jetson is how a filesystem gets corrupted, and this board is yours for
fourteen more weeks, so the session you lose to that is your own.

Check that the label on the chassis matches the `device_id` in your report. That string identifies
every record you file for the rest of the course.

Bring `system_report.json` to Lab 02. The environment verification runs against it, so a missing
report costs you next week as well as this one.

**A system claim is worthless without a command that verifies it.**

---

## Notes for whoever finalises this handout

Three reconciliations are outstanding against
`labs/lab01/ENEE459L_Lab01_Platform_Bringup.pptx`, and all three are content changes rather than
formatting.

**Slide 4, move 02, reads "Flash and first boot."** Students do not flash. The microSD is written
during imaging because twenty simultaneous 20 GB writes do not fit in a session — see
`docs/10_bringup_procedure.md` §3. The move should read "First boot and identity."

**Slide 4's timings sum to 105 minutes of hands-on**, which overruns the 110-minute session as soon
as any mini-lecture happens. Doc 10 §3.3 proposes 15 / 15 / 25 / 15 / 10 with 20 for the briefing
and 10 for the checkpoint. Time the Phase 2 dry run and reconcile.

**Slide 6, "Ribbon reversed," says "Contacts face the board."** That rule was written when the
camera was believed to be a native 22-pin module. The delivered camera is 15-pin and reaches the
board through a conversion ribbon, so there are two connectors with two orientations and the single
rule is not safe at both ends. Since students no longer seat the ribbon at all, the slide should
either be re-cut around the doc 07 §4 shot 3 photographs as a *thing to recognise* rather than a
thing to do, or replaced with a different third failure mode.

---

## Sources

- Full bring-up procedure and every open item behind this handout — `docs/10_bringup_procedure.md`
- Lab 01 scope and the failure mode taught — `docs/03_syllabus_map.md` §3
- Ribbon handling rationale — `docs/04_risk_register.md` R-18
- Preflight checks behind Stage D — `docs/05_phase2_runbook.md` §4
- Measured-value token rules — `docs/06_measured_backfill_register.md`
- The coding half of this lab — `labs/lab01/starter/README.md`
