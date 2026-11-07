# Lab 09 — What an engine is bound to?

An engine is not a faster model. It is a model that has been told which machine it is for.

That sentence is the whole lab. A TensorRT plan is faster than the model it came from, and it is faster because it stopped being a model — it gave up every axis it could have chosen at run time, every version it could have run under, and every device it could have run on, and each of those is a price somebody paid on your behalf. You will find out what was paid.

## What is this lab is built around

This lab is built around profiling execution latency and rigorously verifying output agreement between different inference backends, ensuring that optimizations do not introduce timing instabilities, numerical divergence, or classification flips. Specifically, it centers on:

- Timing Analysis and Performance Profiling: Measuring execution durations across backends, identifying sample distributions and worst-case tail latencies, computing timing jitter, and evaluating whether a backend delivers meaningful speedup and execution time savings.
- Floating-Point Output Divergence: Characterizing the absolute and relative numerical differences between backend outputs without failing quietly on non-finite values (NaNs or infinities), while handling near-zero denominators using a strictly positive floor.
- Decision Parity and Invariance Certification: Evaluating whether two backends pick the same class on an input-by-input basis, and measuring decision margins between top scores to verify whether measured output deviations can flip any model predictions.

## What You Will Build

Throughout this lab, you will build:

- `latency_report`: A timing analysis function that processes an iterable of backend durations to return sample count (n), arithmetic mean (mean), percentiles (p50, p95, p99 via linear interpolation), maximum execution time (worst), and distribution stability (jitter = p95 - p50), while rejecting negative or non-finite measurements.

- `speedup`: A comparative performance metric function that computes how much faster an optimized backend is relative to a baseline, reporting both the multiplicative acceleration factor (factor = base / other, with faster as True when factor > 1) and the signed absolute difference (saved_ms = base - other).

- `max_abs_dev`: An array comparison function that measures the peak absolute difference (max_abs) between two backend output sequences, recording the flat index where it occurs (index, broken by lowest index on ties), the corresponding values (a, b), and the sequence length (n).

- `max_rel_dev`: A relative comparison function that computes the largest quotient of absolute difference over the reference magnitude bounded by a floor (max(abs(b[i]), floor)), returning the maximum relative error (max_rel), its flat index (index), the count of denominators that required clamping (floored), the smallest reference magnitude seen (denom_min), and the sequence length (n).

- `top1_agreement`: A decision consistency evaluator that checks whether two backends select identical top-1 argmax classes across paired score vectors (breaking ties by lowest index), returning total inputs (n), agreement count (agree), mismatch count (disagree), overall match percentage (rate), and the row index of the first divergence (first_disagreement).

- `decision_margin`: A prediction safety certifier that calculates the gap between the top-scoring and runner-up classes for every input row, reporting the minimum margin (min), its row index (argmin), median and mean margins, how many margins fall below a measured deviation tolerance (below_tol), and whether no decisions can be flipped by that deviation (safe = True when below_tol == 0).


## How to Write code

The instructions for writing the code are provided in slides in `Module 1` on ELMS. The slide numbers for each of the function are mentioned below -

1. latency_report: pages 1-2
2. speedup: page 3
3. max_abs_dev: pages 4-5
4. max_rel_dev: pages 5-6
5. top1_agreement: pages 7-8
6. decision_margin: pages 8-9

## How to clone lab07 code

```
git remote add upstream https://github.com/YOUR_USERNAME/YOUR_REPO.git
git pull upstream main
git push origin main
```

## How to Run

```bash
cd lab09/

# Generate the report on the board
python agreement.py
```

## How to Debug your code

There is only one way to debug code - 
1. One way is to use breakpoints. For that, we use `pdb` the package and `pdb.set_trace()` to add a breakpoint at any line of code. 

## How to save your work

For saving your work, you create a new branch named `solution9` by running the following command.
```bash
git switch -c solution9
```

After this, push your changes with following set of commands - 
```bash
git add .
git commit -m "Adding things"
git push -u origin solution9
```

## Before you hand in
Run your code and verify that its output matches the provided sample files. Once you have confirmed that everything is working correctly, push your changes to a new branch. Before submitting the link to your branch on Canvas, please verify that the branch contains the code you wrote and that all of your changes have been successfully pushed.
