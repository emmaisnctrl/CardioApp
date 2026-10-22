import os
import warnings
import numpy as np
import wfdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (Input, Conv1D, MaxPooling1D, Flatten,
                                     Dense, Dropout, BatchNormalization)
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical

warnings.filterwarnings("ignore")

# ── CONFIGURATION ────────────────────────────────────────────
DATASET_PATH = r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0"
FS = 125               # Hz
SEGMENT_LENGTH = 625   # 5 seconds
STEP = 312             # 2.5 seconds between windows
EPOCHS = 30            # early stopping will usually end it sooner
HERE = os.path.dirname(os.path.abspath(__file__))

# ── RATE LABELLING (AHA thresholds), applied per 5-second window ──
# The CNN only learns what the waveform can show: heart rate pattern.
#   HR > 100        -> Tachycardia
#   HR 60 to 100    -> Normal
#   HR < 60         -> dropped (too few windows to learn; Bradycardia is
#                      decided from the measured HR at runtime instead)
def label_rate(hr):
    if hr > 100:
        return "Tachycardia"
    if hr >= 60:
        return "Normal"
    return None

# Same filter the Flask backend applies at runtime
def bandpass(signal, low=0.5, high=4.0, order=3):
    nyq = 0.5 * FS
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, signal)

def find_channel(names, key):
    return next((i for i, s in enumerate(names) if key in s), None)

# ── LOAD DATA ────────────────────────────────────────────────
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
        if p_idx is None or hr_idx is None:
            continue

        ppg = rec.p_signal[:, p_idx].astype(np.float64)
        nans = np.isnan(ppg)
        if nans.all():
            continue
        if nans.any():  # fill gaps so timing stays aligned with the numerics
            ppg[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), ppg[~nans])

        ppg = bandpass(ppg)
        hr_series = num.p_signal[:, hr_idx]
        sp_series = num.p_signal[:, sp_idx] if sp_idx is not None else None

        for start in range(0, len(ppg) - SEGMENT_LENGTH, STEP):
            sec = start // FS
            hr = np.nanmedian(hr_series[sec:sec + 5])
            if np.isnan(hr) or hr < 20:
                dropped += 1
                continue
            # Sensor dropout (SpO2 reading near 0) means the probe was off
            if sp_series is not None:
                sp = np.nanmedian(sp_series[sec:sec + 5])
                if not np.isnan(sp) and sp < 50:
                    dropped += 1
                    continue

            label = label_rate(hr)
            if label is None:
                dropped += 1
                continue

            seg = ppg[start:start + SEGMENT_LENGTH]
            lo, hi = seg.min(), seg.max()
            if hi - lo < 1e-6:
                continue
            X.append(((seg - lo) / (hi - lo)).astype(np.float32))
            y.append(label)
            groups.append(i)  # patient id, used to split by patient

        print(f"  Loaded {name}")
    print(f"\nWindows kept: {len(X)} | dropped: {dropped}")
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

def describe(name, idx, y, groups, classes):
    counts = {c: int((y[idx] == k).sum()) for k, c in enumerate(classes)}
    print(f"{name}: patients {sorted(set(groups[idx]))} | windows {counts}")

def train():
    X, y_text, groups = load_dataset()

    encoder = LabelEncoder()
    y = encoder.fit_transform(y_text)
    classes = list(encoder.classes_)
    n_classes = len(classes)
    print("Classes found:", classes)

    # Split BY PATIENT, keeping both classes in every split:
    # about 20% test, 20% validation (for early stopping), 60% train
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    rest_idx, test_idx = next(outer.split(X, y, groups))
    inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=7)
    tr, va = next(inner.split(X[rest_idx], y[rest_idx], groups[rest_idx]))
    train_idx, val_idx = rest_idx[tr], rest_idx[va]

    describe("Train", train_idx, y, groups, classes)
    describe("Val  ", val_idx, y, groups, classes)
    describe("Test ", test_idx, y, groups, classes)

    X = X.reshape(X.shape[0], SEGMENT_LENGTH, 1)
    Y = to_categorical(y, num_classes=n_classes)

    weights = compute_class_weight("balanced", classes=np.unique(y[train_idx]), y=y[train_idx])
    class_weight = {int(c): float(w) for c, w in zip(np.unique(y[train_idx]), weights)}

    model = build_model(n_classes)
    history = model.fit(
        X[train_idx], Y[train_idx],
        validation_data=(X[val_idx], Y[val_idx]),
        epochs=EPOCHS, batch_size=64, class_weight=class_weight,
        callbacks=[EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)],
        verbose=1,
    )

    # ── Final evaluation on patients the model never saw ──
    probs = model.predict(X[test_idx], verbose=0)
    pred = np.argmax(probs, axis=1)
    acc = float((pred == y[test_idx]).mean())
    majority = max((y[test_idx] == k).mean() for k in range(n_classes))
    print(f"\nTest accuracy (unseen patients): {acc * 100:.2f}%")
    print(f"Baseline if it always guessed the biggest class: {majority * 100:.2f}%")
    if n_classes == 2:
        print(f"ROC AUC: {roc_auc_score(y[test_idx], probs[:, 1]):.3f}")
    print("\nPer-class report:")
    print(classification_report(y[test_idx], pred, target_names=classes, zero_division=0))
    print("Confusion matrix (rows = true, columns = predicted):")
    print(confusion_matrix(y[test_idx], pred))

    # Keep the current 5-class model as a backup (model_old.h5 is NOT touched)
    cur = os.path.join(HERE, "model.h5")
    if os.path.exists(cur):
        os.replace(cur, os.path.join(HERE, "model_5class_v2.h5"))
    model.save(cur)
    np.save(os.path.join(HERE, "label_classes.npy"), encoder.classes_)
    print("\nSaved model.h5 and label_classes.npy (previous model kept as model_5class_v2.h5)")

    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Train")
    plt.plot(history.history["val_accuracy"], label="Validation")
    plt.title("Accuracy"); plt.xlabel("Epoch"); plt.legend()
    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Train")
    plt.plot(history.history["val_loss"], label="Validation")
    plt.title("Loss"); plt.xlabel("Epoch"); plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "training_history_v3.png"))

if __name__ == "__main__":
    train()