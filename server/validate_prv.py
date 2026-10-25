import os
import csv
import warnings
import numpy as np
import wfdb
from scipy.signal import butter, filtfilt, find_peaks, resample
from scipy.stats import spearmanr

# Reuse the app's own functions so we are testing the real code
from app.ml.predict import (
    bandpass_filter, normalise, estimate_bpm_fft, analyse_pulse, BPM_AGREEMENT,
)

warnings.filterwarnings("ignore")

DATASET_PATH = r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0"
FS = 125
WINDOW_S = 30
TRIM_START = 2 * FS
TRIM_END = 1 * FS
CAMERA_FPS = 20.0
HERE = os.path.dirname(os.path.abspath(__file__))


def find_channel(names, key):
    return next((i for i, s in enumerate(names) if key in s), None)


def fill_gaps(x):
    x = x.astype(np.float64)
    bad = np.isnan(x)
    if bad.all():
        return None
    if bad.any():
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), x[~bad])
    return x


def ecg_variability(ecg_seg):
    """
    Finds ECG heartbeats with a simple detector (band-pass, squared slope,
    smoothing, peak picking) and returns (RMSSD in ms, mean RR in ms).
    """
    nyq = 0.5 * FS
    b, a = butter(2, [5 / nyq, 15 / nyq], btype="band")
    x = filtfilt(b, a, ecg_seg)
    w = int(0.12 * FS)
    energy = np.convolve(np.diff(x, prepend=x[0]) ** 2, np.ones(w) / w, mode="same")
    peaks, _ = find_peaks(energy, height=0.25 * np.percentile(energy, 99),
                          distance=int(0.3 * FS))
    # Move each detection onto the largest deflection nearby
    half = int(0.06 * FS)
    refined = []
    for p in peaks:
        lo, hi = max(0, p - half), min(len(x), p + half)
        refined.append(lo + int(np.argmax(np.abs(x[lo:hi]))))
    refined = np.unique(refined)
    if len(refined) < 10:
        return None, None
    rr = np.diff(refined) / FS
    valid = (rr >= 0.3) & (rr <= 1.5)       # same believable range as the PPG side
    if valid.sum() < 10:
        return None, None
    pair_ok = valid[:-1] & valid[1:]
    d = np.diff(rr)[pair_ok]
    if len(d) < 8:
        return None, None
    return float(np.sqrt(np.mean(d ** 2)) * 1000), float(rr[valid].mean() * 1000)


def ppg_variability(raw125):
    """The app's own pulse analysis on one 30-second window at 125 Hz."""
    signal = bandpass_filter(raw125)[TRIM_START:-TRIM_END]
    full = normalise(signal)
    if full is None:
        return None
    pulse = analyse_pulse(signal, 200.0, 0.0, None)   # brightness checks skipped
    bb, fft = pulse["bpm_from_beats"], estimate_bpm_fft(full)
    agree = bb is not None and fft is not None and abs(bb - fft) / fft <= BPM_AGREEMENT
    if pulse["quality"] == "Poor" or not agree or pulse["rmssd_ms"] is None:
        return None
    return {"rmssd": pulse["rmssd_ms"], "ibi": pulse["mean_ibi_ms"]}


def degrade_to_camera(raw125):
    """Imitate a ~20 fps phone video, then resample as the app does."""
    n = len(raw125)
    n_cam = int(n / FS * CAMERA_FPS)
    cam = np.interp(np.arange(n_cam) / CAMERA_FPS, np.arange(n) / FS, raw125)
    return resample(cam, int(len(cam) / CAMERA_FPS * FS))


def report(label, ecg_vals, ppg_vals):
    e, p = np.array(ecg_vals), np.array(ppg_vals)
    if len(e) < 5:
        print(f"{label}: not enough windows")
        return
    err = p - e
    rho = spearmanr(e, p).correlation
    print(f"{label}: n={len(e)} | median ECG {np.median(e):.1f} ms, PPG {np.median(p):.1f} ms | "
          f"mean error (PPG minus ECG) {err.mean():+.1f} ms | MAE {np.abs(err).mean():.1f} ms | "
          f"within 10 ms {np.mean(np.abs(err) <= 10) * 100:.1f}% | Spearman rho {rho:.2f}")


rows = []
for i in range(1, 54):
    name = f"bidmc{i:02d}"
    try:
        rec = wfdb.rdrecord(os.path.join(DATASET_PATH, name))
    except Exception as e:
        print("Skipping", name, e)
        continue
    p_idx = find_channel(rec.sig_name, "PLETH")
    e_idx = find_channel(rec.sig_name, "II")
    if p_idx is None or e_idx is None:
        continue
    ppg = fill_gaps(rec.p_signal[:, p_idx])
    ecg = fill_gaps(rec.p_signal[:, e_idx])
    if ppg is None or ecg is None:
        continue

    for start_s in range(0, int(len(ppg) / FS) - WINDOW_S + 1, WINDOW_S):
        a = start_s * FS
        raw = ppg[a:a + WINDOW_S * FS]
        ecg_seg = ecg[a + TRIM_START:a + WINDOW_S * FS - TRIM_END]
        if raw.max() - raw.min() < 1e-6 or ecg_seg.max() - ecg_seg.min() < 1e-6:
            continue
        ecg_rmssd, ecg_rr = ecg_variability(ecg_seg)
        if ecg_rmssd is None:
            continue
        full_res = ppg_variability(raw)
        cam_res = ppg_variability(degrade_to_camera(raw))
        rows.append({"record": name, "start_s": start_s, "ecg_rmssd": ecg_rmssd,
                     "ecg_rr": ecg_rr, "full": full_res, "cam": cam_res})
    print("Done", name)

print(f"\nWindows with a usable ECG reference: {len(rows)}\n")
for tag, key in (("125 Hz", "full"), ("about 20 fps", "cam")):
    both = [r for r in rows if r[key] is not None]
    print(f"--- PPG at {tag}: {len(both)} windows passed the app's quality gate ---")
    report("Mean beat interval", [r["ecg_rr"] for r in both], [r[key]["ibi"] for r in both])
    report("PRV (RMSSD)", [r["ecg_rmssd"] for r in both], [r[key]["rmssd"] for r in both])
    print()

out = os.path.join(HERE, "prv_validation.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["record", "start_s", "ecg_rmssd_ms", "ecg_mean_rr_ms",
                "ppg125_rmssd_ms", "ppg125_ibi_ms", "ppg20_rmssd_ms", "ppg20_ibi_ms"])
    for r in rows:
        f_, c_ = r["full"], r["cam"]
        w.writerow([r["record"], r["start_s"], round(r["ecg_rmssd"], 1), round(r["ecg_rr"], 1),
                    f_["rmssd"] if f_ else "", f_["ibi"] if f_ else "",
                    c_["rmssd"] if c_ else "", c_["ibi"] if c_ else ""])
print("Saved", out)