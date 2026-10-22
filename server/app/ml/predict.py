import numpy as np
import cv2
import os
from scipy.signal import butter, filtfilt, find_peaks, resample
from tensorflow.keras.models import load_model

# ── LOAD MODEL AND LABELS ONCE AT STARTUP ───────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
model = load_model(os.path.join(BASE_DIR, "model.h5"))
label_classes = np.load(os.path.join(BASE_DIR, "label_classes.npy"), allow_pickle=True)

SAMPLING_RATE = 125   # Hz, the rate the model was trained on
SEGMENT_LENGTH = 625  # 5 seconds of signal at 125 Hz
SETTLE_SECONDS = 2    # discard the first 2 s while the finger settles
MIN_SECONDS = 8       # shortest scan we accept

# Experimental SpO2 formula: SpO2 = SPO2_A - SPO2_B * R
# These are generic textbook values. They are NOT calibrated for any phone.
SPO2_A = 110.0
SPO2_B = 25.0

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

# ── EXTRACT HEART RATE ───────────────────────────────────────
def extract_heart_rate(signal, fs=SAMPLING_RATE):
    """Counts peaks (heartbeats) and converts the average gap to BPM."""
    peaks, _ = find_peaks(signal, distance=int(fs * 0.4), height=0.3)
    if len(peaks) < 2:
        return None
    bpm = 60.0 / (np.mean(np.diff(peaks)) / fs)
    return round(bpm, 1) if 30 <= bpm <= 220 else None

# ── EXPERIMENTAL SpO2 ESTIMATE ───────────────────────────────
def estimate_spo2(raw, trim):
    """
    'Ratio of ratios' method. For each colour channel:
        pulsatile part (AC) / steady part (DC)
    then R = (AC/DC of red) / (AC/DC of blue).
    The estimate is a straight-line function of R. It is experimental
    and uncalibrated, so it must be presented as an estimate only.
    """
    if raw.shape[1] < 2:
        return None, None
    ratios = []
    for ch in (0, 1):
        sig = raw[:, ch]
        dc = float(np.mean(sig[trim:]))
        ac = float(np.std(bandpass_filter(sig)[trim:]))
        # A saturated or empty channel has no pulse to measure
        if dc <= 1 or ac < 1e-3:
            return None, None
        ratios.append(ac / dc)
    r = ratios[0] / ratios[1]
    spo2 = float(np.clip(SPO2_A - SPO2_B * r, 70, 100))
    return round(spo2, 1), round(float(r), 3)

# ── PREPROCESS SIGNAL ────────────────────────────────────────
def preprocess_signal(raw_signal, fps=30.0):
    raw = np.array(raw_signal, dtype=np.float32)
    if raw.ndim == 1:               # single-channel input (red only)
        raw = raw[:, None]
    raw = raw[~np.isnan(raw).any(axis=1)]

    if len(raw) < fps * MIN_SECONDS:
        return None, None, None, "Scan too short. Keep your finger still for at least 8 seconds."

    # Resample using the REAL duration so 125 Hz means 125 Hz
    n_samples = int(len(raw) / fps * SAMPLING_RATE)
    raw = resample(raw, n_samples, axis=0)
    trim = SETTLE_SECONDS * SAMPLING_RATE

    # Red channel drives heart rate and the CNN
    signal = bandpass_filter(raw[:, 0])[trim:]
    if len(signal) < SEGMENT_LENGTH:
        return None, None, None, "Scan too short after trimming. Try a longer scan."

    full = normalise(signal)
    segment = normalise(signal[:SEGMENT_LENGTH])
    if full is None or segment is None:
        return None, None, None, "Flat signal detected. Make sure your finger covers the camera."

    heart_rate = extract_heart_rate(full)

    spo2, ratio = estimate_spo2(raw, trim)
    print(f"SpO2 ratio R = {ratio} | estimate = {spo2}")   # note these for calibration

    return segment, heart_rate, spo2, None

# ── MAIN PREDICTION FUNCTION ─────────────────────────────────
def predict_condition(raw_signal, fps=30.0):
    segment, heart_rate, spo2, error = preprocess_signal(raw_signal, fps)
    if error:
        return {"error": error}
    if heart_rate is None:
        return {"error": "Could not detect a steady pulse. Keep your finger still, cover the lens and flash fully, and try again."}

    # CNN: Normal vs Tachycardia from the waveform pattern
    probs = model.predict(segment.reshape(1, SEGMENT_LENGTH, 1), verbose=0)[0]
    idx = int(np.argmax(probs))
    cnn_label = str(label_classes[idx])
    confidence = round(float(probs[idx]) * 100, 1)

    # Final decision combines the CNN with the measured heart rate
    if heart_rate < 60:
        condition, basis, confidence = "Bradycardia", "Heart-rate threshold (AHA)", None
    elif cnn_label == "Tachycardia" and heart_rate > 100:
        condition, basis = "Tachycardia", "CNN model and measured heart rate"
    elif cnn_label == "Normal" and heart_rate <= 100:
        condition, basis = "Normal", "CNN model and measured heart rate"
    else:
        condition, basis = "Inconclusive", "Model and heart rate disagree. Please scan again"

    return {
        "condition": condition,
        "confidence": confidence,
        "heart_rate": heart_rate,
        "spo2": spo2,          # experimental estimate, may be None
        "basis": basis,
    }