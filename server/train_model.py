import numpy as np
import pandas as pd
import wfdb
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils import resample
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.utils import to_categorical
import matplotlib.pyplot as plt

# ── CONFIGURATION ────────────────────────────────────────────
DATASET_PATH = r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0"
SEGMENT_LENGTH = 625   # 5 seconds at 125Hz
STEP_SIZE = 125        # 1 second step between segments (overlap)
SAMPLING_RATE = 125    # Hz
NUM_CLASSES = 5
MODEL_OUTPUT_PATH = "model.h5"

# ── THRESHOLD LABELLING ──────────────────────────────────────
# Based on WHO (2011) and AHA (2023) clinical thresholds
def label_condition(hr, spo2):
    if hr > 100:
        return "Tachycardia"
    elif hr < 60:
        return "Bradycardia"
    elif spo2 < 90:
        return "Critical Hypoxemia"
    elif spo2 < 95:
        return "Mild Hypoxemia"
    else:
        return "Normal"

# ── LOAD AND SEGMENT DATA ────────────────────────────────────
def load_dataset():
    segments = []
    labels = []
    skipped = 0

    print("Loading BIDMC dataset...")

    for i in range(1, 54):  # bidmc01 to bidmc53
        record_name = f"bidmc{i:02d}"
        record_path = os.path.join(DATASET_PATH, record_name)

        try:
            # Read the waveform record (.dat and .hea files)
            record = wfdb.rdrecord(record_path)

            # Read the numerics record which contains HR and SpO2
            numerics = wfdb.rdrecord(record_path + "n")

            # Extract the PPG signal (PLETH channel)
            signal_names = list(record.sig_name)
            pleth_index = next((i for i, s in enumerate(signal_names) if "PLETH" in s), None)
            if pleth_index is None:
                print(f"  Skipping {record_name}: no PLETH channel")
                skipped += 1
                continue
            ppg_signal = record.p_signal[:, pleth_index]

            # Extract HR and SpO2 from numerics
            numeric_names = list(numerics.sig_name)
            hr_index = next((i for i, s in enumerate(numeric_names) if "HR" in s), None)
            spo2_index = next((i for i, s in enumerate(numeric_names) if "SpO2" in s), None)

            if hr_index is None or spo2_index is None:
                print(f"  Skipping {record_name}: missing HR or SpO2")
                skipped += 1
                continue

            # Get median HR and SpO2 for the whole recording
            hr_values = numerics.p_signal[:, hr_index]
            spo2_values = numerics.p_signal[:, spo2_index]

            # Remove NaN values before taking median
            hr = np.nanmedian(hr_values)
            spo2 = np.nanmedian(spo2_values)

            if np.isnan(hr) or np.isnan(spo2):
                print(f"  Skipping {record_name}: NaN HR or SpO2")
                skipped += 1
                continue

            # Apply clinical threshold labelling
            condition = label_condition(hr, spo2)

            # Remove NaN values from PPG signal
            ppg_signal = ppg_signal[~np.isnan(ppg_signal)]

            if len(ppg_signal) < SEGMENT_LENGTH:
                print(f"  Skipping {record_name}: signal too short")
                skipped += 1
                continue

            # Chop the signal into overlapping 5 second segments
            for start in range(0, len(ppg_signal) - SEGMENT_LENGTH, STEP_SIZE):
                segment = ppg_signal[start:start + SEGMENT_LENGTH]

                # Normalise segment to range 0-1
                seg_min = segment.min()
                seg_max = segment.max()
                if seg_max - seg_min == 0:
                    continue  # skip flat segments
                segment = (segment - seg_min) / (seg_max - seg_min)

                segments.append(segment)
                labels.append(condition)

            print(f"  Loaded {record_name} — HR: {hr:.1f}, SpO2: {spo2:.1f}% → {condition}")

        except Exception as e:
            print(f"  Error loading {record_name}: {e}")
            skipped += 1
            continue

    print(f"\nTotal segments: {len(segments)}")
    print(f"Skipped records: {skipped}")
    return np.array(segments), np.array(labels)

# ── BUILD 1D CNN MODEL ───────────────────────────────────────
def build_model(input_shape, num_classes):
    model = Sequential([
        # First convolutional block — extracts low level waveform features
        Conv1D(32, kernel_size=5, activation="relu", input_shape=input_shape),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),

        # Second convolutional block — extracts higher level patterns
        Conv1D(64, kernel_size=5, activation="relu"),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),

        # Third convolutional block — deepest feature extraction
        Conv1D(128, kernel_size=3, activation="relu"),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        Dropout(0.3),

        # Flatten and classify
        Flatten(),
        Dense(128, activation="relu"),
        Dropout(0.4),
        Dense(num_classes, activation="softmax")  # 5 output classes
    ])

    model.compile(
        optimizer="adam",
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )
    return model

# ── MAIN TRAINING PIPELINE ───────────────────────────────────
def train():
    # Load data
    X, y_labels = load_dataset()

    if len(X) == 0:
        print("No data loaded. Check your dataset path.")
        return

    # Print class distribution before balancing
    unique, counts = np.unique(y_labels, return_counts=True)
    print("\nClass distribution before balancing:")
    for cls, cnt in zip(unique, counts):
        print(f"  {cls}: {cnt} segments")

    # Balance classes by oversampling minority classes
    # This prevents the model from being biased toward Normal
    df = pd.DataFrame({"label": y_labels, "index": range(len(X))})
    max_count = df["label"].value_counts().max()
    balanced_indices = []

    for label in df["label"].unique():
        label_indices = df[df["label"] == label]["index"].values
        resampled = resample(label_indices, replace=True, n_samples=max_count, random_state=42)
        balanced_indices.extend(resampled)

    X = X[balanced_indices]
    y_labels = y_labels[balanced_indices]

    print(f"\nAfter balancing: {len(X)} total segments")

    # Encode string labels to integers
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y_labels)
    y_categorical = to_categorical(y_encoded, num_classes=NUM_CLASSES)

    print(f"\nClasses: {list(encoder.classes_)}")

    # Save label encoder classes for use in Flask
    np.save("label_classes.npy", encoder.classes_)
    print("Saved label_classes.npy")

    # Reshape for CNN input: (samples, timesteps, channels)
    X = X.reshape(X.shape[0], X.shape[1], 1)

    # Split into training and testing sets (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_categorical, test_size=0.2, random_state=42, stratify=y_encoded[balanced_indices] if len(balanced_indices) == len(X) else y_encoded
    )

    print(f"\nTraining samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")

    # Build and summarise the model
    model = build_model(input_shape=(SEGMENT_LENGTH, 1), num_classes=NUM_CLASSES)
    model.summary()

    # Train the model
    print("\nTraining started...")
    history = model.fit(
        X_train, y_train,
        epochs=20,
        batch_size=32,
        validation_data=(X_test, y_test),
        verbose=1
    )

    # Evaluate on test set
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest Accuracy: {accuracy * 100:.2f}%")
    print(f"Test Loss: {loss:.4f}")

    # Save the trained model
    model.save(MODEL_OUTPUT_PATH)
    print(f"\nModel saved to {MODEL_OUTPUT_PATH}")

    # Plot training history
    plt.figure(figsize=(12, 4))

    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Train Accuracy")
    plt.plot(history.history["val_accuracy"], label="Val Accuracy")
    plt.title("Model Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Val Loss")
    plt.title("Model Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()

    plt.tight_layout()
    plt.savefig("training_history.png")
    print("Training history plot saved to training_history.png")

if __name__ == "__main__":
    train()