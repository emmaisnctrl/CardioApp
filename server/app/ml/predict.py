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

# ── EXTRACT RED CHANNEL FROM VIDEO ──────────────────────────
def extract_ppg_from_video(video_path):
    """
    Reads the video and returns the mean red value of every frame,
    plus the video's real frame rate (needed to get the timing right).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, None, "Could not open video file"

    # Real frame rate of the recording; fall back to 30 if it looks wrong
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 5 or fps > 120:
        fps = 30.0

    red_values = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # OpenCV frames are BGR, so index 2 is the red channel
        red_values.append(np.mean(frame[:, :, 2]))
    cap.release()

    print(f"Extracted {len(red_values)} frames at {fps:.1f} fps")

    if len(red_values) < 10:
        return None, None, "Video too short or unreadable"
    return np.array(red_values, dtype=np.float32), fps, None

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
    # Reject physiologically impossible values
    return round(bpm, 1) if 30 <= bpm <= 220 else None

# ── PREPROCESS SIGNAL ────────────────────────────────────────
def preprocess_signal(raw_signal, fps=30.0):
    signal = np.array(raw_signal, dtype=np.float32)
    signal = signal[~np.isnan(signal)]

    if len(signal) < fps * MIN_SECONDS:
        return None, None, "Scan too short. Keep your finger still for at least 8 seconds."

    # Resample using the REAL duration so 125 Hz means 125 Hz
    duration = len(signal) / fps
    signal = resample(signal, int(duration * SAMPLING_RATE))

    # Filter the whole recording, then drop the settling period
    signal = bandpass_filter(signal)
    signal = signal[SETTLE_SECONDS * SAMPLING_RATE:]

    if len(signal) < SEGMENT_LENGTH:
        return None, None, "Scan too short after trimming. Try a longer scan."

    full = normalise(signal)
    if full is None:
        return None, None, "Flat signal detected. Make sure your finger covers the camera."

    # Heart rate from the whole clean recording (more accurate than 5 s)
    heart_rate = extract_heart_rate(full)

    # The model sees one 5 s window, normalised on its own
    segment = normalise(signal[:SEGMENT_LENGTH])
    return segment, heart_rate, None

# ── MAIN PREDICTION FUNCTION ─────────────────────────────────
def predict_condition(raw_signal, fps=30.0):
    segment, heart_rate, error = preprocess_signal(raw_signal, fps)
    if error:
        return {"error": error}

    X = segment.reshape(1, SEGMENT_LENGTH, 1)
    predictions = model.predict(X, verbose=0)
    idx = int(np.argmax(predictions[0]))
    condition = str(label_classes[idx])

    # SpO2 is an ESTIMATE based on the predicted condition, not a measurement
    spo2_estimates = {
        "Normal": 98.0, "Tachycardia": 97.0, "Bradycardia": 97.0,
        "Mild Hypoxemia": 92.0, "Critical Hypoxemia": 87.0,
    }

    return {
        "condition": condition,
        "confidence": round(float(predictions[0][idx]) * 100, 1),
        "heart_rate": heart_rate,
        "spo2": spo2_estimates.get(condition, 97.0),
    }