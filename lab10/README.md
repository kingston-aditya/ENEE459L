# Lab 10 — Microphones on Jetson Nanos

Every number this module works on was produced at the bench by `arecord` and by four lines of Python that read the file. What is left is arithmetic, and the arithmetic is the part that catches the mistakes.

That sentence is the whole lab. A WAV file header might claim 44,100 Hz over a file captured at 16,000 Hz, a byte count might not be a whole number of frames because a capture was killed mid-write, a peak at 0.999 might hide four thousand samples flat against the rail, or a peak at 0.008 might only be using six of its sixteen bits. By concentrating format geometry, full-scale decibel conversions, and metadata audits into strict verification routines, you will catch hardware, gain, and documentation failures before an audio recording ever reaches a downstream model.

## What is this lab is built around

This lab is built around verifying WAV file geometry, analyzing signal amplitude and bit utilization relative to full scale, and auditing capture session records to ensure that audio recordings are intact, properly gained, and completely documented. Specifically, it centers on:

- **WAV Format Geometry and Header Consistency**: Computing exact byte counts, frame strides, and recording durations from raw PCM parameters, catching truncated captures where byte counts do not divide evenly into whole frames, and verifying that the binary WAV header agrees with the session's stated configuration.
- **Full-Scale Amplitude and Bit Utilization Analysis**: Converting normalized linear amplitudes in `[0, 1]` to decibels relative to full scale (dBFS) while forcing callers to handle digital silence (`0.0` returning `None` rather than `-inf`), quantifying how many of the format's bits a signal peak actually reaches, and formatting human-readable level and clipping summaries.
- **Session Metadata Completeness Auditing**: Checking recording session logs against the thirteen benchmark capture choices—separating parameters stored inside the WAV header from the ten handwritten decisions recorded nowhere else—and flagging missing or blank entries.

## What You Will Build

Throughout this lab, you will build:

- `wav_bytes`: A file sizing function that computes how large a PCM WAV of a given description is, returning the rounded sample count (`samples`), frame stride (`block_align`), bytes per second (`byte_rate`), payload size (`data_bytes`), header size (`header_bytes`), and overall file footprint (`total_bytes`).

- `duration_from_bytes`: A byte-chunk verification function that calculates how long a data payload is and whether it divides evenly into whole frames, returning the complete sample count (`samples`), duration in seconds (`seconds`), leftover bytes (`remainder`), and an alignment flag (`whole = True` when `remainder == 0`).

- `header_consistency`: A cross-check function that compares a WAV header dictionary against a session's audio metadata across `sample_rate`, `channels`, and `bit_depth`, returning an agreement flag (`agree`), a list of field discrepancies (`mismatches`), the recomputed duration dictionary from the header's byte count (`duration`), and the stated duration (`stated_seconds`).

- `dbfs`: A logarithmic level conversion function that maps a normalized magnitude in `[0, 1]` to decibels relative to full scale (`20.0 * log10(amplitude)`), explicitly returning `None` for digital silence (`0.0`) so downstream JSON serializers and tables never encounter `-inf`, while rejecting negative numbers.

- `bits_in_use`: A resolution metric function that calculates how many of a format's bits a peak at `peak_dbfs` actually reaches (`max(0.0, bit_depth + peak_dbfs / DB_PER_BIT)`), returning `0.0` when `peak_dbfs` is `None` (digital silence).

- `level_sentence`: A report formatter that summarizes a `level_report` dictionary into a single line—reporting digital silence when all samples are zero, or formatting peak dBFS, RMS dBFS, crest factor in dB, and the count and percentage of clipped samples at the rail.

- `record_gaps`: A Stage E checklist auditor that inspects a session record against the thirteen required capture choices (`THIRTEEN_CHOICES`), categorizing keys into `present`, `missing`, and `blank` (present but empty/whitespace), while reporting overall completion (`complete`), fields carried by the WAV header (`in_header`), and fields that must be recorded by hand (`hand_written`).

- `record_sentence`: A summary formatter that condenses a `record_gaps` dictionary into a single human-readable line stating either that all choices are named (breaking down header vs. handwritten counts) or listing the exact keys that are missing or left blank.

## How to Record Audio

1. Connect the microphone to Jetson Nano.
2. Run the bash command - `arecord -l`
3. Find your card and device number. In example below, card number is 2 and device number is 0. 
```bash
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin Nano APE], device 19: tegra-dlink-19 XBAR-ADMAIF20-19 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```
4. Use command `arecord -D plughw:2,0 -f S16_LE -r 44100 -c 1 -d 10 test_voice.wav` to record a 10 sec audio. `-d 10` sets the time in seconds.

## How to Write code

The instructions for writing the code are provided in slides in `Module 1` on ELMS. The slide numbers for each of the function are mentioned below -

1. `wav_bytes`: pages 1-2
2. `duration_from_bytes`: page 3
3. `header_consistency`: pages 4-5
4. `dbfs`: page 6
5. `bits_in_use`: page 7
6. `level_sentence`: page 8
7. `record_gaps`: pages 9-10
8. `record_sentence`: page 11

## How to clone lab07 code

```bash
git remote add upstream [https://github.com/YOUR_USERNAME/YOUR_REPO.git](https://github.com/YOUR_USERNAME/YOUR_REPO.git)
git pull upstream main
git push origin main
```

## How to Run

```bash
cd lab10/

# Generate the capture and level verification report
python capture.py
```

## How to Debug your code

There is only one way to debug code - 
1. One way is to use breakpoints. For that, we use `pdb` the package and `pdb.set_trace()` to add a breakpoint at any line of code. 

## How to save your work

For saving your work, you create a new branch named `solution10` by running the following command.
```bash
git switch -c solution10
```

After this, push your changes with following set of commands - 
```bash
git add .
git commit -m "Implement audio capture and level verification functions"
git push -u origin solution10
```

## Before you hand in
Run your code and verify that its output matches the provided sample files. Once you have confirmed that everything is working correctly, push your changes to a new branch. Before submitting the link to your branch on Canvas, please verify that the branch contains the code you wrote and that all of your changes have been successfully pushed.