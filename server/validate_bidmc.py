import os
import csv
import warnings
from collections import Counter
import numpy as np
import wfdb
from scipy.signal import resample

# Reuse the app's own functions so we are testing the real code
from app.ml.predict import (
    bandpass_filter, normalise, extract_heart_rate, estimate_bpm_fft,
    analyse_pulse, VARIABLE_CV, IRREGULAR_CV, BPM_AGREEMENT,
)

warnings.filterwarnings("ignore")

DATASET_PATH = r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0"
FS = 125                 # BIDMC sampling rate (Hz)
WINDOW_S = 30            # same length as a phone scan
TRIM_START = 2 * FS      # same trimming as the app
TRIM_END = 1 * FS
CAMERA_FPS = 20.0        # what your phone records at

HERE = os.path.dirname(os.path.abspath(__file__))


def find_channel(names, key):
    return next((i for i, s in enumerate(names) if key in s), None)


def run_pipeline(raw125):
    """The app's pipeline on one 30-second window sampled at 125 Hz."""
    filtered = bandpass_filter(raw125)
    signal = filtered[TRIM_START:-TRIM_END]
    full = normalise(signal)
    if full is None:
        return None
    # Brightness checks are skipped (BIDMC is not a camera)
    pulse = analyse_pulse(signal, 200.0, 0.0, None)
    bb = pulse["bpm_from_beats"]
    fft = estimate_bpm_fft(full)
    old = extract_heart_rate(full)
    agree = bb is not None and fft is not None and abs(bb - fft) / fft <= BPM_AGREEMENT
    return {
        "bb": bb, "fft": fft, "old": old,
        "cv": pulse["cv"], "rmssd": pulse["rmssd_ms"],
        "regularity": pulse["regularity"],
        "passed": pulse["quality"] != "Poor" and agree,
    }


def degrade_to_camera(raw125):
    """Imitate a ~20 fps phone video: sample at 20 fps, then resample as the app does."""
    n = len(raw125)
    t125 = np.arange(n) / FS
    n_cam = int(n / FS * CAMERA_FPS)
    cam = np.interp(np.arange(n_cam) / CAMERA_FPS, t125, raw125)
    return resample(cam, int(len(cam) / CAMERA_FPS * FS))


def stats(label, pairs):
    """pairs = list of (estimate, reference)."""
    if not pairs:
        print(f"{label:<36} no data")
        return
    err = np.array([e - r for e, r in pairs])
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))
    within5 = np.mean(np.abs(err) <= 5) * 100
    print(f"{label:<36} n={len(pairs):<5} MAE={mae:5.1f}  RMSE={rmse:5.1f}  within 5 BPM={within5:5.1f}%")


rows = []
for i in range(1, 54):
    name = f"bidmc{i:02d}"
    path = os.path.join(DATASET_PATH, name)
    try:
        rec = wfdb.rdrecord(path)
        num = wfdb.rdrecord(path + "n")
    except Exception as e:
        print("Skipping", name, e)
        continue
    p_idx = find_channel(rec.sig_name, "PLETH")
    h_idx = find_channel(num.sig_name, "HR")
    if p_idx is None or h_idx is None:
        continue

    ppg = rec.p_signal[:, p_idx].astype(np.float64)
    bad = np.isnan(ppg)
    if bad.all():
        continue
    if bad.any():
        ppg[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), ppg[~bad])
    hr_ref = num.p_signal[:, h_idx]

    for start_s in range(0, int(len(ppg) / FS) - WINDOW_S + 1, WINDOW_S):
        a = start_s * FS
        raw = ppg[a:a + WINDOW_S * FS]
        if raw.max() - raw.min() < 1e-6:
            continue
        # Reference heart rate over the same (trimmed) seconds
        ref = np.nanmean(hr_ref[start_s + 2:start_s + WINDOW_S - 1])
        if np.isnan(ref) or ref < 30:
            continue
        full_res = run_pipeline(raw)
        cam_res = run_pipeline(degrade_to_camera(raw))
        if full_res is None or cam_res is None:
            continue
        rows.append({"record": name, "start_s": start_s, "ref": float(ref),
                     "full": full_res, "cam": cam_res})
    print("Done", name)

print(f"\nWindows analysed: {len(rows)} (30 s each, from {len(set(r['record'] for r in rows))} patients)\n")

# ── PART A: heart-rate accuracy at the full 125 Hz ──────────────
print("PART A: heart rate vs the hospital's recorded heart rate (125 Hz)")
for label, key in (("Original peak method", "old"),
                   ("FFT method", "fft"),
                   ("New beat method", "bb")):
    stats(label, [(r["full"][key], r["ref"]) for r in rows if r["full"][key] is not None])
passed = [r for r in rows if r["full"]["passed"]]
stats("New beat method, passed the gate",
      [(r["full"]["bb"], r["ref"]) for r in passed])
print(f"Share of windows passing the quality gate: {100 * len(passed) / len(rows):.1f}%")

# ── PART B: the same at about 20 fps (phone frame rate) ─────────
print("\nPART B: the same test with the signal reduced to about 20 fps")
passed_cam = [r for r in rows if r["cam"]["passed"]]
stats("New beat method, passed the gate",
      [(r["cam"]["bb"], r["ref"]) for r in passed_cam])
print(f"Share of windows passing the quality gate: {100 * len(passed_cam) / len(rows):.1f}%")

# ── PART C: effect of 20 fps on regularity and PRV ──────────────
both = [r for r in rows if r["full"]["passed"] and r["cam"]["passed"]]
print(f"\nPART C: regularity and PRV, {len(both)} windows that passed at both rates")
if both:
    def label(cv):
        return ("Possibly irregular" if cv >= IRREGULAR_CV
                else "Slightly variable" if cv >= VARIABLE_CV else "Regular")
    print("Label share at 125 Hz:", dict(Counter(r["full"]["regularity"] for r in both)))
    print("Label share at 20 fps:", dict(Counter(r["cam"]["regularity"] for r in both)))
    changed = np.mean([r["full"]["regularity"] != r["cam"]["regularity"] for r in both]) * 100
    print(f"Windows whose regularity label changed at 20 fps: {changed:.1f}%")
    rm = [(r["full"]["rmssd"], r["cam"]["rmssd"]) for r in both
          if r["full"]["rmssd"] is not None and r["cam"]["rmssd"] is not None]
    if rm:
        print(f"Median PRV (RMSSD): {np.median([a for a, _ in rm]):.1f} ms at 125 Hz, "
              f"{np.median([b for _, b in rm]):.1f} ms at 20 fps")

# ── Save every window to a file for the appendix ────────────────
out = os.path.join(HERE, "bidmc_validation.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["record", "start_s", "ref_hr", "bb_125", "fft_125", "old_125", "passed_125",
                "cv_125", "rmssd_125", "reg_125", "bb_20", "passed_20", "cv_20", "rmssd_20", "reg_20"])
    for r in rows:
        a, b = r["full"], r["cam"]
        w.writerow([r["record"], r["start_s"], round(r["ref"], 1), a["bb"], a["fft"], a["old"],
                    a["passed"], a["cv"], a["rmssd"], a["regularity"],
                    b["bb"], b["passed"], b["cv"], b["rmssd"], b["regularity"]])
print("\nSaved", out)