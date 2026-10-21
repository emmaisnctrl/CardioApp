import os
import warnings
import numpy as np
import wfdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (Input, Conv1D, MaxPooling1D, Flatten,
                                     Dense, Dropout, BatchNormalization)
from tensorflow.keras.utils import to_categorical

warnings.filterwarnings("ignore")

# ── CONFIGURATION ────────────────────────────────────────────
DATASET_PATH = r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0"
FS = 125               # Hz
SEGMENT_LENGTH = 625   # 5 seconds
STEP = 312             # 2.5 seconds between windows
EPOCHS = 15
HERE = os.path.dirname(os.path.abspath(__file__))

# ── THRESHOLD LABELLING (WHO / AHA), applied per window ──────
def label_condition(hr, spo2):
    if hr > 100:
        return "Tachycardia"
    if hr < 60:
        return "Bradycardia"
    if spo2 < 90:
        return "Critical Hypoxemia"
    if spo2 < 95:
        return "Mild Hypoxemia"
    return "Normal"

# Same filter the Flask backend applies at runtime
def bandpass(signal, low=0.5, high=4.0, order=3):
    nyq = 0.5 * FS
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, signal)

def find_channel(names, key):
    return next((i for i, s in enumerate(names) if key in s), None)

# ── LOAD DATA: ONE LABEL PER 5-SECOND WINDOW ─────────────────
def load_dataset():
    X, y, groups = [], [], []
    dropped = 0
    for i in range(1, 54):
        name = f"bidmc{i:02d}"
        path = os.path.join(DATASET_PATH, name)
        try:
            rec = wfdb.rdrecord(path)           # waveform at 125 Hz
            num = wfdb.rdrecord(path + "n")     # numerics at 1 Hz
        except Exception as e:
            print(f"  Skipping {name}: {e}")
            continue

        p_idx = find_channel(rec.sig_name, "PLETH")
        hr_idx = find_channel(num.sig_name, "HR")
        sp_idx = find_channel(num.sig_name, "SpO2")
        if p_idx is None or hr_idx is None or sp_idx is None:
            continue

        ppg = rec.p_signal[:, p_idx].astype(np.float64)
        nans = np.isnan(ppg)
        if nans.all():
            continue
        if nans.any():  # fill gaps so timing stays aligned with the numerics
            ppg[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), ppg[~nans])

        ppg = bandpass(ppg)
        hr_series = num.p_signal[:, hr_idx]
        sp_series = num.p_signal[:, sp_idx]

        for start in range(0, len(ppg) - SEGMENT_LENGTH, STEP):
            sec = start // FS
            hr = np.nanmedian(hr_series[sec:sec + 5])
            spo2 = np.nanmedian(sp_series[sec:sec + 5])

            # Skip missing values and sensor dropouts (e.g. SpO2 reading 0)
            if np.isnan(hr) or np.isnan(spo2) or spo2 < 50 or hr < 20:
                dropped += 1
                continue

            seg = ppg[start:start + SEGMENT_LENGTH]
            lo, hi = seg.min(), seg.max()
            if hi - lo < 1e-6:
                continue
            X.append(((seg - lo) / (hi - lo)).astype(np.float32))
            y.append(label_condition(hr, spo2))
            groups.append(i)  # patient id, used to split by patient

        print(f"  Loaded {name}")
    print(f"\nWindows kept: {len(X)} | dropped (missing or dropout): {dropped}")
    return np.array(X), np.array(y), np.array(groups)

# ── SAME ARCHITECTURE AS BEFORE (so the report still matches) ─
def build_model(n_classes):
    model = Sequential([
        Input(shape=(SEGMENT_LENGTH, 1)),
        Conv1D(32, 5, activation="relu"), BatchNormalization(), MaxPooling1D(2), Dropout(0.2),
        Conv1D(64, 5, activation="relu"), BatchNormalization(), MaxPooling1D(2), Dropout(0.2),
        Conv1D(128, 3, activation="relu"), BatchNormalization(), MaxPooling1D(2), Dropout(0.3),
        Flatten(), Dense(128, activation="relu"), Dropout(0.4),
        Dense(n_classes, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    return model

def train():
    X, y_text, groups = load_dataset()

    encoder = LabelEncoder()
    y = encoder.fit_transform(y_text)
    n_classes = len(encoder.classes_)
    print("Classes found:", list(encoder.classes_))

    # Split BY PATIENT: no patient appears in both train and test
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    print("Test patients:", sorted(set(groups[test_idx])))

    for label, idx in (("Train", train_idx), ("Test", test_idx)):
        counts = {c: int((y[idx] == k).sum()) for k, c in enumerate(encoder.classes_)}
        print(f"{label} windows per class: {counts}")

    X = X.reshape(X.shape[0], SEGMENT_LENGTH, 1)
    Y = to_categorical(y, num_classes=n_classes)

    # Class weights instead of duplicating samples
    present = np.unique(y[train_idx])
    weights = compute_class_weight("balanced", classes=present, y=y[train_idx])
    class_weight = {int(c): float(w) for c, w in zip(present, weights)}

    model = build_model(n_classes)
    history = model.fit(
        X[train_idx], Y[train_idx],
        validation_data=(X[test_idx], Y[test_idx]),
        epochs=EPOCHS, batch_size=64,
        class_weight=class_weight, verbose=1,
    )

    loss, acc = model.evaluate(X[test_idx], Y[test_idx], verbose=0)
    print(f"\nTest accuracy (unseen patients): {acc * 100:.2f}%  | loss: {loss:.4f}")

    pred = np.argmax(model.predict(X[test_idx], verbose=0), axis=1)
    labels = list(range(n_classes))
    print("\nPer-class report:")
    print(classification_report(y[test_idx], pred, labels=labels,
                                target_names=encoder.classes_, zero_division=0))
    print("Confusion matrix (rows = true, columns = predicted):")
    print(confusion_matrix(y[test_idx], pred, labels=labels))

    # Keep the old model as a backup, then save the new one
    old = os.path.join(HERE, "model.h5")
    if os.path.exists(old):
        os.replace(old, os.path.join(HERE, "model_old.h5"))
    model.save(os.path.join(HERE, "model.h5"))
    np.save(os.path.join(HERE, "label_classes.npy"), encoder.classes_)
    print("\nSaved model.h5 and label_classes.npy (old model kept as model_old.h5)")

    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Train")
    plt.plot(history.history["val_accuracy"], label="Test")
    plt.title("Accuracy"); plt.xlabel("Epoch"); plt.legend()
    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Train")
    plt.plot(history.history["val_loss"], label="Test")
    plt.title("Loss"); plt.xlabel("Epoch"); plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "training_history_v2.png"))

if __name__ == "__main__":
    train()