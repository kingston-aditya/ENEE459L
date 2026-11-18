# Lab 11 — A score is not an event

Every number this module works on was produced at the bench by `arecord` and by sliding-window detector scores computed from the audio. What is left is arithmetic, state logic, and temporal matching—and those three are the parts that catch the mistakes.

That sentence is the whole lab. A model with a 0.001 false-positive rate per window still fires 36 times an hour at a 0.1-second hop, a single threshold sitting on noisy probabilities chatters into dozens of duplicate detections for one spoken word, a plan with `leave > enter` or `hop_s > window_s` fails before the stream even starts, and a detector evaluated without hysteresis, voting, or refractory muting turns a clean recording into an alarm clock. By validating streaming plans (`0_stream.py`), separating raw window-level decisions (`1_decide.py`) from temporal event smoothing and onset matching (`2_events.py`), you will turn raw confidence traces into reliable spoken-event detections.

## What is this lab is built around

This lab is built around validating streaming detector plans, evaluating imbalanced window-level decisions, and applying temporal smoothing and onset matching to extract discrete spoken events from continuous probability traces. Specifically, it centers on:

- **Streaming Plan and Session Schema Validation (`0_stream.py`)**: Checking the fifteen streaming parameters and three pre-computed arithmetic targets (`ring_ms`, `latency_ms`, `decisions_per_hour`) to catch impossible detector configurations (`k > n`, inverted hysteresis `leave > enter`, or `hop_s > window_s`) before audio ever streams.
- **Window-Level Confusion Matrices and Base-Rate Precision (`1_decide.py`)**: Building confusion matrices (`tp`, `fp`, `tn`, `fn`) where true negatives dominate, safely returning `None` for undefined ratios instead of `0.0`, and calculating real-world precision when rare spoken events are evaluated at 36,000 decisions per hour.
- **Temporal Event Smoothing and Collar Matching (`2_events.py`)**: Suppressing score chatter using causal trailing `k`-of-`n` window voting, dual-threshold hysteresis (`enter` / `leave`), and rising-edge refractory muting, then matching predicted onsets against ground truth within a timing collar.

## What You Will Build

Throughout this lab, you will build **8 functions** across `0_stream.py` (1), `1_decide.py` (3), and `2_events.py` (4):

- `_validate_plan` (in `0_stream.py`): A streaming plan validator that checks all required plan keys (`REQUIRED_PLAN`), verifies positive integers/durations and score bounds in `[0, 1]`, enforces `k <= n`, `leave <= enter`, and `hop_s <= window_s`, and confirms positive pre-computed `stated` values (`ring_ms`, `latency_ms`, `decisions_per_hour`).

- `confusion` (in `1_decide.py`): A window-level classification counter that evaluates `score >= threshold` against binary integer labels (`0` or `1`), returning `tp`, `fp`, `tn`, `fn`, and `windows` while intentionally omitting accuracy.

- `rates` (in `1_decide.py`): A ratio calculator that derives `tpr`, `fpr`, `precision`, `recall`, and `f1` from a confusion matrix dictionary, returning `None` whenever a denominator is zero so a silent detector (`precision = None`) is never confused with an all-wrong detector (`precision = 0.0`).

- `precision_at_base_rate` (in `1_decide.py`): A base-rate precision estimator that computes hourly decisions (`3600 / hop_s`), positive and negative window counts, `expected_tp`, `expected_fp`, `precision`, and `base_rate` without premature rounding.

- `k_of_n` (in `2_events.py`): A causal trailing window voter that outputs `True` at index `i` whenever at least `k` of the flags in `max(0, i - n + 1)` through `i` inclusive are `True`, scoring partial prefixes at the start of the stream so an immediate positive burst fires at index `k - 1`.

- `hysteresis` (in `2_events.py`): A dual-threshold state filter that latches `True` when `score >= enter` and stays `True` until `score < leave`, keeping the detector active when a score sits directly on `leave`.

- `refractory` (in `2_events.py`): A rising-edge debouncer that converts rising edges (`False -> True` transitions, including index `0` if `True`) into timestamps `idx * hop_s` and suppresses any subsequent edge within `refractory_s` of the last accepted onset without restarting the timer on suppressed edges.

- `match_events` (in `2_events.py`): A greedy truth-order onset matcher that pairs each `truth_s` timestamp with the nearest unused `predicted_s` timestamp within `±collar_s` (breaking ties by earlier prediction), returning `matches` (with signed `delta_s = predicted_s - truth_s`), `hits`, `misses`, `false_alarms`, and `collar_s`.

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

The instructions for writing the code are provided in slides in `Module` on ELMS. The slide numbers for each of the function are mentioned below -

1. `_validate_plan (0_stream.py)`: pages 1-2
2. `confusion (1_decide.py)`: pages 3-4
3. `rates (1_decide.py)`: pages 5-6
4. `precision_at_base_rate (1_decide.py)`: pages 7-8
5. `k_of_n (2_events.py)`: pages 9-10
6. `hysteresis (2_events.py)`: page 11
7. `refractory (2_events.py)`: page 12
8. `match_events (2_events.py)`: pages 13-14

## How to clone lab11 code

```bash
git remote add upstream [https://github.com/YOUR_USERNAME/YOUR_REPO.git](https://github.com/YOUR_USERNAME/YOUR_REPO.git)
git pull upstream main
git push origin main
```

## How to Run

```bash
cd lab11/

# Generate the capture and level verification report
python3 0_stream.py test_voice.wav -o session.json

# Run window-level decision metrics and save JSON output
python3 1_decide.py test_voice.wav -o decide_session.json

# Run Stage E event smoothing & onset matching and save JSON output
python3 2_events.py test_voice.wav -o events_session.json
```

## How to Debug your code

There is only one way to debug code - 
1. One way is to use breakpoints. For that, we use `pdb` the package and `pdb.set_trace()` to add a breakpoint at any line of code. 

## How to save your work

For saving your work, you create a new branch named `solution11` by running the following command.
```bash
git switch -c solution11
```

After this, push your changes with following set of commands - 
```bash
git add .
git commit -m "Implement audio capture and level verification functions"
git push -u origin solution11
```

## Before you hand in
Run your code and verify that its output matches the provided sample files. Once you have confirmed that everything is working correctly, push your changes to a new branch. Before submitting the link to your branch on Canvas, please verify that the branch contains the code you wrote and that all of your changes have been successfully pushed.