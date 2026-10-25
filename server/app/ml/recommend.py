import os
import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Check the current model name in the Groq console; the built-in advice
# below covers you if this name is wrong or the key is missing.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

SYSTEM_PROMPT = (
    "You are a cautious health-information assistant inside a cardiovascular "
    "screening app. You are not a doctor and must not diagnose. In at most 3 short "
    "sentences of plain English, explain what the measurements may mean and give "
    "one practical next step. Never name hypertension, heart failure or any disease "
    "as a conclusion. Never mention oxygen saturation or SpO2. If beat-timing "
    "variation is mentioned, say it is often caused by breathing, movement or a "
    "noisy signal and that repeated scans matter more than one. Suggest a validated "
    "blood pressure device or an ECG only as a follow-up when readings repeatedly "
    "look concerning. Advise seeing a health professional if the person has chest "
    "pain, fainting, dizziness or breathlessness."
)


def fallback_recommendation(condition, heart_rate, state, regularity, basis):
    """Built-in advice used when Groq is unavailable."""
    hr = f"{heart_rate:.0f} BPM" if heart_rate else "your measured rate"
    basis = basis or ""

    if condition == "Normal":
        if "Borderline low" in basis:
            text = (f"Your heart rate ({hr}) is just under 60, which is common at rest, "
                    "especially in active people. It matters mainly if you also feel "
                    "dizzy, faint or unusually tired. Scan again after resting to confirm.")
        elif "Borderline high" in basis:
            text = (f"Your heart rate ({hr}) is slightly above 100. Caffeine, stress, a "
                    "warm room or recent activity can all raise it. Rest for 10 minutes "
                    "and scan again.")
        else:
            text = (f"Your heart rate ({hr}) is within the normal resting range. Keep up "
                    "regular activity, drink enough water and sleep well. Scanning at the "
                    "same time each day gives the most useful trend.")
    elif condition == "Elevated (after activity)":
        text = (f"Your heart rate ({hr}) is raised, which is expected soon after "
                "activity. Rest for 10 to 15 minutes, drink water and scan again.")
    elif condition == "Tachycardia":
        text = (f"Your heart rate ({hr}) is above 100 BPM. Rest quietly, avoid caffeine and "
                "scan again in 15 minutes. If it stays high on repeated resting scans, "
                "consider having your blood pressure checked with a validated device and "
                "speak to a health professional. Seek help promptly for chest pain, "
                "fainting or breathlessness.")
    elif condition == "Bradycardia":
        text = (f"Your heart rate ({hr}) is below 55 BPM. This can be normal at rest, "
                "especially for very active people. If you feel dizzy, faint or unusually "
                "tired, speak to a health professional.")
    else:
        text = ("The scan gave mixed signals, so no result was reached. Sit still for a few "
                "minutes, cover the lens and flash fully with your fingertip, and scan again.")

    if regularity == "Possibly irregular":
        text += (" Your beat-to-beat timing varied more than usual in this scan, which is "
                 "often caused by breathing, movement or a noisy signal. Repeat the scan at "
                 "rest, and if it keeps appearing, ask a clinician whether an ECG is worthwhile.")
    return text


def get_recommendation(condition, heart_rate, state, regularity=None, basis=None):
    key = os.environ.get("GROQ_API_KEY")
    if key:
        try:
            prompt = (f"Result: {condition}. Heart rate: {heart_rate} BPM. "
                      f"State before scanning: {state}. "
                      f"Pulse regularity: {regularity or 'not assessed'}. "
                      f"Basis: {basis or 'n/a'}.")
            resp = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 160,
                },
                timeout=8,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text:
                return text
        except Exception as e:
            print("Groq unavailable, using built-in advice:", e)
    return fallback_recommendation(condition, heart_rate, state, regularity, basis)