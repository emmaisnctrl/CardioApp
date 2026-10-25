import numpy as np
import cv2
import os
from datetime import datetime
import matplotlib
matplotlib.use("Agg")   # draw plots to files, no window needed
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks, resample
from tensorflow.keras.models import load_model

# ── LOAD MODEL AND LABELS ONCE AT STARTUP ───────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
model = load_model(os.path.join(BASE_DIR, "model.h5"))
label_classes = np.load(os.path.join(BASE_DIR, "label_classes.npy"), allow_pickle=True)

SAMPLING_RATE = 125   # Hz, the rate the model was trained on
SEGMENT_LENGTH = 625  # 5 seconds of signal at 125 Hz
SETTLE_SECONDS = 2    # discard the first 2 s while the finger settles
TAIL_SECONDS = 1      # discard the last second (the finger often lifts)
MIN_SECONDS = 8       # shortest scan we accept

# Experimental SpO2 formula: SpO2 = SPO2_A - SPO2_B * R (uncalibrated)
SPO2_A = 110.0
SPO2_B = 25.0

# ── HEART-RATE THRESHOLDS (AHA) AND CAMERA TOLERANCE ────────
HR_LOW = 60          # below this is a low resting heart rate
HR_HIGH = 100        # above this is a high resting heart rate
HR_TOLERANCE = 5     # +/- BPM allowed for camera measurement error

# ── PULSE ANALYSIS SETTINGS (provisional, tune on your own scans) ──
PEAK_PROMINENCE = 0.15   # how clearly a peak must stand out (signal is 0 to 1)
IBI_MIN = 0.3            # shortest believable gap between beats (seconds)
IBI_MAX = 1.5            # longest believable gap between beats (seconds)
VARIABLE_CV = 0.15       # gap spread at or above this = "Slightly variable"
IRREGULAR_CV = 0.25      # gap spread at or above this = "Possibly irregular"
FINGER_MIN_RED = 80      # mean red below this = finger probably not on the camera
MIN_RED_BLUE = 3.0       # red/blue ratio below this = no finger on the lens and flash
CLIP_LEVEL = 250         # red value at which the image counts as saturated
MAX_CLIP_FRACTION = 0.2  # more than 20% saturated frames = unreliable
BPM_AGREEMENT = 0.10     # beat-based and FFT heart rates must agree within 10%

# ── EXTRACT RED + BLUE CHANNELS FROM VIDEO ──────────────────
def extract_ppg_from_video(video_path):
    """
    Returns an array with one row per frame: [mean red, mean blue],
    plus the video's real frame rate.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, None, "Could not open video file"

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 5 or fps > 120:
        fps = 30.0

    red_values, blue_values = [], []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        red_values.append(np.mean(frame[:, :, 2]))   # BGR: index 2 = red
        blue_values.append(np.mean(frame[:, :, 0]))  # index 0 = blue
    cap.release()

    print(f"Extracted {len(red_values)} frames at {fps:.1f} fps")

    if len(red_values) < 10:
        return None, None, "Video too short or unreadable"
    signal = np.stack([red_values, blue_values], axis=1).astype(np.float32)
    return signal, fps, None

# ── BANDPASS FILTER ──────────────────────────────────────────
def bandpass_filter(signal, lowcut=0.5, highcut=4.0, fs=SAMPLING_RATE, order=3):
    """Keeps only 0.5 to 4 Hz (30 to 240 BPM); everything else is noise."""
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype="band")
    return filtfilt(b, a, signal)

# ── NORMALISE TO 0-1 ─────────────────────────────────────────
def normalise(signal):
    lo, hi = signal.min(), signal.max()
    if hi - lo == 0:
        return None
    return (signal - lo) / (hi - lo)

# ── ORIGINAL HEART-RATE METHOD (kept only for comparison) ────
def extract_heart_rate(signal, fs=SAMPLING_RATE):
    """Counts peaks and converts the average gap to BPM."""
    peaks, _ = find_peaks(signal, distance=int(fs * 0.4), height=0.3)
    if len(peaks) < 2:
        return None
    bpm = 60.0 / (np.mean(np.diff(peaks)) / fs)
    return round(bpm, 1) if 30 <= bpm <= 220 else None

# ── INDEPENDENT HEART-RATE CHECK USING THE FFT ───────────────
def estimate_bpm_fft(signal, fs=SAMPLING_RATE):
    """
    Finds the strongest repeating frequency in the signal (42 to 180 BPM).
    It does not pick individual peaks, so it is a good independent check.
    """
    x = signal - signal.mean()
    n = 1 << 14   # zero-padding gives finer frequency steps
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), n=n))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    band = (freqs >= 0.7) & (freqs <= 3.0)
    if not band.any():
        return None
    return round(float(freqs[band][np.argmax(spectrum[band])]) * 60.0, 1)

# ── EXPERIMENTAL SpO2 ESTIMATE (unchanged) ───────────────────
def estimate_spo2(raw, trim):
    """
    'Ratio of ratios' method on red and blue. Experimental and
    uncalibrated, so it must be presented as an estimate only.
    """
    if raw.shape[1] < 2:
        return None, None
    ratios = []
    for ch in (0, 1):
        sig = raw[:, ch]
        dc = float(np.mean(sig[trim:]))
        ac = float(np.std(bandpass_filter(sig)[trim:]))
        if dc <= 1 or ac < 1e-3:
            return None, None
        ratios.append(ac / dc)
    r = ratios[0] / ratios[1]
    spo2 = float(np.clip(SPO2_A - SPO2_B * r, 70, 100))
    return round(spo2, 1), round(float(r), 3)

# ── FIND INDIVIDUAL HEARTBEATS ───────────────────────────────
def detect_beats(signal, fs=SAMPLING_RATE):
    """
    Two passes. Pass 1 finds rough peaks to estimate the typical gap.
    Pass 2 repeats the search, forbidding peaks closer than 60% of that gap,
    which removes most double-counted beats.
    """
    first, _ = find_peaks(signal, distance=int(fs * 0.3), prominence=PEAK_PROMINENCE)
    if len(first) < 3:
        return first
    typical_gap = np.median(np.diff(first))
    min_gap = max(int(typical_gap * 0.6), int(fs * 0.3))
    peaks, _ = find_peaks(signal, distance=min_gap, prominence=PEAK_PROMINENCE)
    return peaks

# ── SAVE A PICTURE OF THE SIGNAL AND BOTH PEAK METHODS ───────
def save_debug_plot(full, fs=SAMPLING_RATE):
    """
    Saves the filtered signal with the peaks found by the original method
    (red x) and the new method (green circles) into debug_plots.
    """
    try:
        folder = os.path.join(BASE_DIR, "debug_plots")
        os.makedirs(folder, exist_ok=True)
        old_peaks, _ = find_peaks(full, distance=int(fs * 0.4), height=0.3)
        new_peaks = detect_beats(full, fs)
        t = np.arange(len(full)) / fs
        plt.figure(figsize=(14, 4))
        plt.plot(t, full, linewidth=1)
        plt.plot(t[old_peaks], full[old_peaks], "rx", markersize=8,
                 label=f"original method: {len(old_peaks)} peaks")
        plt.plot(t[new_peaks], full[new_peaks], "go", markerfacecolor="none",
                 markersize=9, label=f"new method: {len(new_peaks)} peaks")
        plt.xlabel("seconds")
        plt.title("Filtered PPG signal with detected beats")
        plt.legend(loc="upper right")
        plt.tight_layout()
        name = datetime.now().strftime("scan_%H%M%S.png")
        plt.savefig(os.path.join(folder, name), dpi=110)
        plt.close()
        print("Debug plot saved:", name)
    except Exception as e:
        print("Plot failed:", e)

# ── PULSE QUALITY, REGULARITY AND VARIABILITY ────────────────
def analyse_pulse(signal, mean_red, clip_fraction, red_blue=None, fs=SAMPLING_RATE):
    """
    Works out the gaps between heartbeats, checks the scan quality,
    and (only if quality allows) reports regularity and PRV (RMSSD).
    """
    result = {
        "quality": "Poor", "reason": "", "n_beats": 0, "n_rejected": 0,
        "mean_ibi_ms": None, "cv": None, "rmssd_ms": None,
        "regularity": "Not enough clean beats", "bpm_from_beats": None,
    }

    # Brightness and colour checks on the raw camera values
    if mean_red < FINGER_MIN_RED:
        result["reason"] = "Finger not detected on the camera"
        return result
    # With a finger over the flash the image is strongly red; without it, it is not
    if red_blue is not None and red_blue < MIN_RED_BLUE:
        result["reason"] = "Finger not detected on the camera"
        return result
    if clip_fraction > MAX_CLIP_FRACTION:
        result["reason"] = "Image too bright (signal clipped)"
        return result

    sig = normalise(signal)
    if sig is None:
        result["reason"] = "Flat signal"
        return result

    peaks = detect_beats(sig, fs)
    result["n_beats"] = int(len(peaks))
    if len(peaks) < 4:
        result["reason"] = "Too few beats detected"
        return result

    # Gaps between successive beats, in seconds
    ibi = np.diff(peaks) / fs
    valid = (ibi >= IBI_MIN) & (ibi <= IBI_MAX)   # only impossible gaps are rejected
    n_rejected = int((~valid).sum())
    good = ibi[valid]
    result["n_rejected"] = n_rejected

    if len(good) < 10:
        result["reason"] = "Too few clean beats"
        return result

    mean_ibi = float(good.mean())
    cv = float(good.std() / mean_ibi)   # spread of the gaps relative to their average
    result["mean_ibi_ms"] = round(mean_ibi * 1000, 0)
    result["cv"] = round(cv, 3)
    result["bpm_from_beats"] = round(60.0 / mean_ibi, 1)

    # PRV (RMSSD): average beat-to-beat change, using only neighbouring valid gaps
    pair_ok = valid[:-1] & valid[1:]
    diffs = np.diff(ibi)[pair_ok]
    if len(diffs) >= 8:
        result["rmssd_ms"] = round(float(np.sqrt(np.mean(diffs ** 2))) * 1000, 1)

    # Quality grade from the number of usable beats and the share rejected
    rejected_fraction = n_rejected / len(ibi)
    if len(good) >= 20 and rejected_fraction <= 0.10:
        result["quality"] = "Good"
    elif len(good) >= 12 and rejected_fraction <= 0.25:
        result["quality"] = "Fair"
    else:
        result["reason"] = "Too many unusable beats"
        return result

    # Three levels: only the top one is called "Possibly irregular"
    if cv >= IRREGULAR_CV:
        result["regularity"] = "Possibly irregular"
    elif cv >= VARIABLE_CV:
        result["regularity"] = "Slightly variable"
    else:
        result["regularity"] = "Regular"
    return result

# ── PREPROCESS SIGNAL ────────────────────────────────────────
def preprocess_signal(raw_signal, fps=30.0):
    raw = np.array(raw_signal, dtype=np.float32)
    if raw.ndim == 1:               # single-channel input (red only)
        raw = raw[:, None]
    raw = raw[~np.isnan(raw).any(axis=1)]

    if len(raw) < fps * MIN_SECONDS:
        return None, None, None, None, "Scan too short. Keep your finger still for at least 8 seconds."

    # Brightness and colour checks use the raw values, before any resampling
    mean_red = float(np.mean(raw[:, 0]))
    mean_blue = float(np.mean(raw[:, 1])) if raw.shape[1] > 1 else None
    red_blue = (mean_red / mean_blue) if mean_blue else None
    clip_fraction = float(np.mean(raw[:, 0] >= CLIP_LEVEL))

    # Resample using the REAL duration so 125 Hz means 125 Hz
    n_samples = int(len(raw) / fps * SAMPLING_RATE)
    raw = resample(raw, n_samples, axis=0)
    trim = SETTLE_SECONDS * SAMPLING_RATE
    tail = TAIL_SECONDS * SAMPLING_RATE

    # Filter, then drop the settling period at the start and the lift-off at the end
    filtered = bandpass_filter(raw[:, 0])
    signal = filtered[trim:-tail]
    if len(signal) < SEGMENT_LENGTH:
        return None, None, None, None, "Scan too short after trimming. Try a longer scan."

    full = normalise(signal)
    segment = normalise(signal[:SEGMENT_LENGTH])
    if full is None or segment is None:
        return None, None, None, None, "Flat signal detected. Make sure your finger covers the camera."

    bpm_old = extract_heart_rate(full)     # original method, comparison only
    bpm_fft = estimate_bpm_fft(full)       # independent check

    pulse = analyse_pulse(signal, mean_red, clip_fraction, red_blue)

    # Agreement gate: two independent methods must give the same heart rate.
    # If they don't, the pulse is unclear and the scan is rejected.
    bb = pulse["bpm_from_beats"]
    heart_rate = bb if bb is not None else bpm_fft
    if pulse["quality"] != "Poor":
        if bb is None or bpm_fft is None or abs(bb - bpm_fft) / bpm_fft > BPM_AGREEMENT:
            pulse["quality"] = "Poor"
            pulse["reason"] = "Pulse unclear (heart-rate methods disagree)"
            pulse["regularity"] = "Not enough clean beats"

    rb_text = f"{red_blue:.1f}" if red_blue is not None else "n/a"
    print(
        f"PULSE | quality={pulse['quality']} ({pulse['reason'] or 'ok'}) | "
        f"beats={pulse['n_beats']} rejected={pulse['n_rejected']} | "
        f"mean_red={mean_red:.0f} red/blue={rb_text} clip={clip_fraction:.2f} | "
        f"CV={pulse['cv']} RMSSD={pulse['rmssd_ms']} ms | "
        f"regularity={pulse['regularity']} | "
        f"BPM(old)={bpm_old} BPM(final)={heart_rate} BPM(beats)={bb} BPM(fft)={bpm_fft}"
    )
    save_debug_plot(full)

    spo2, ratio = estimate_spo2(raw, trim)
    print(f"SpO2 ratio R = {ratio} | estimate = {spo2}")

    return segment, heart_rate, spo2, pulse, None

# ── MAIN PREDICTION FUNCTION ─────────────────────────────────
def predict_condition(raw_signal, fps=30.0, state="Resting"):
    segment, heart_rate, spo2, pulse, error = preprocess_signal(raw_signal, fps)
    if error:
        return {"error": error}
    if heart_rate is None:
        return {"error": "Could not detect a steady pulse. Keep your finger still, cover the lens and flash fully, and try again."}

    # CNN: Normal vs Tachycardia from the waveform pattern (a second opinion)
    probs = model.predict(segment.reshape(1, SEGMENT_LENGTH, 1), verbose=0)[0]
    idx = int(np.argmax(probs))
    cnn_label = str(label_classes[idx])
    confidence = round(float(probs[idx]) * 100, 1)

    low_edge = HR_LOW - HR_TOLERANCE      # 55
    high_edge = HR_HIGH + HR_TOLERANCE    # 105

    if state == "Active" and heart_rate > HR_HIGH:
        # A raised rate soon after activity is expected, so it is not flagged
        condition = "Elevated (after activity)"
        basis = "Expected soon after activity. Rest 10 to 15 minutes and scan again"
        confidence = None
    elif heart_rate < low_edge:
        condition = "Bradycardia"
        basis = "Heart-rate threshold (AHA): below 60 BPM"
        confidence = None
    elif heart_rate < HR_LOW:
        condition = "Normal"
        basis = "Borderline low (55 to 60 BPM), within camera tolerance"
        confidence = None
    elif HR_HIGH < heart_rate <= high_edge:
        condition = "Normal"
        basis = "Borderline high (100 to 105 BPM), within camera tolerance"
        confidence = None
    elif heart_rate > high_edge:
        if cnn_label == "Tachycardia":
            condition, basis = "Tachycardia", "CNN model and measured heart rate"
        else:
            condition, basis = "Inconclusive", "Model and heart rate disagree. Rest and scan again"
            confidence = None
    else:  # 60 to 100 BPM
        if cnn_label == "Normal":
            condition, basis = "Normal", "CNN model and measured heart rate"
        else:
            condition, basis = "Inconclusive", "Model and heart rate disagree. Rest and scan again"
            confidence = None

    return {
        "condition": condition,
        "confidence": confidence,
        "heart_rate": heart_rate,
        "spo2": spo2,          # experimental estimate, may be None
        "basis": basis,
        "pulse": pulse,
    }