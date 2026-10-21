import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Share,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";

// ── RESULT OBJECT SHAPE ───────────────────────────────────────
// This interface defines what the results screen expects to receive.
// When Groq AI is integrated, recommendation will be replaced with
// the actual AI-generated text. When more PPG metrics are added
// (e.g. HRV), they can be added here without restructuring the screen.
interface ScanResult {
  condition: string;
  confidence: string;
  heart_rate: string;
  spo2: string;
  pre_scan_state: string;
  scan_id: string;
  recommendation: string;
  scanned_at: string;
}

// Colour coding for each condition
const CONDITION_COLORS: Record<string, string> = {
  Normal: "#1D9E75",
  Tachycardia: "#E24B4A",
  Bradycardia: "#BA7517",
  "Mild Hypoxemia": "#BA7517",
  "Critical Hypoxemia": "#E24B4A",
};

const CONDITION_ICONS: Record<string, string> = {
  Normal: "✓",
  Tachycardia: "↑",
  Bradycardia: "↓",
  "Mild Hypoxemia": "~",
  "Critical Hypoxemia": "!",
};

export default function ResultsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();

  // Pull values from navigation params, fall back to mock values for testing
  const result: ScanResult = {
    condition: (params.condition as string) || "Normal",
    confidence: (params.confidence as string) || "94.2",
    heart_rate: (params.heart_rate as string) || "76",
    spo2: (params.spo2 as string) || "98",
    pre_scan_state: (params.pre_scan_state as string) || "Resting",
    scan_id: (params.scan_id as string) || "1",
    recommendation: (params.recommendation as string) ||
      "Your readings look healthy. Maintain your current activity level, stay hydrated, and consider scanning again in 24 hours to track your cardiovascular health over time.",
    scanned_at: (params.scanned_at as string) || new Date().toLocaleString(),
  };

  const conditionColor = CONDITION_COLORS[result.condition] || BLUE;
  const conditionIcon = CONDITION_ICONS[result.condition] || "•";
  const confidenceNum = parseFloat(result.confidence);
  const heartRateNum = parseFloat(result.heart_rate);
  const spo2Num = parseFloat(result.spo2);

  // Determine heart rate status label
  const hrStatus =
    heartRateNum > 100 ? "Elevated" :
    heartRateNum < 60 ? "Low" : "Normal";

  // Determine SpO2 status label
  const spo2Status =
    spo2Num < 90 ? "Critical" :
    spo2Num < 95 ? "Low" : "Normal";

  const handleShare = async () => {
    try {
      await Share.share({
        message:
          `CardioApp Scan Result\n` +
          `Date: ${result.scanned_at}\n` +
          `Condition: ${result.condition}\n` +
          `Heart Rate: ${result.heart_rate} BPM\n` +
          `SpO2: ${result.spo2}%\n` +
          `Confidence: ${result.confidence}%\n\n` +
          `Recommendation: ${result.recommendation}\n\n` +
          `CardioApp is a screening tool and does not replace professional medical diagnosis.`,
      });
    } catch (error) {
      console.log("Share error:", error);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Scan Results</Text>
      </View>

      {/* Hero icon */}
      <View style={styles.heroSection}>
        <View style={[styles.heroIcon, { borderColor: conditionColor }]}>
          <Text style={[styles.heroIconText, { color: conditionColor }]}>⚕️</Text>
        </View>
      </View>

      {/* Analysis Complete Badge */}
      <View style={styles.analysisBadge}>
        <Text style={styles.analysisBadgeText}>
          Analysis Complete
        </Text>
        <Text style={styles.analysisBadgeSub}>
          Scanned on {result.scanned_at}
        </Text>
      </View>

      {/* Measurement Cards */}
      <View style={styles.measurementRow}>
        {/* Heart Rate Card */}
        <View style={styles.measurementCard}>
          <View style={styles.measurementCardTop}>
            <Text style={styles.measurementIcon}>🫀</Text>
            <View style={[styles.statusBadge, {
              backgroundColor: hrStatus === "Normal" ? "#E3F2FD" : "#FFF3E0"
            }]}>
              <Text style={[styles.statusBadgeText, {
                color: hrStatus === "Normal" ? BLUE : "#BA7517"
              }]}>{hrStatus.toUpperCase()}</Text>
            </View>
          </View>
          <Text style={styles.measurementLabel}>Heart Rate</Text>
          <Text style={styles.measurementValue}>
            {result.heart_rate !== "null" && result.heart_rate ? result.heart_rate : "--"}
            <Text style={styles.measurementUnit}> BPM</Text>
          </Text>
          <Text style={styles.measurementSub}>Normal range: 60–100 BPM</Text>
        </View>

        {/* SpO2 Card */}
        <View style={styles.measurementCard}>
          <View style={styles.measurementCardTop}>
            <Text style={styles.measurementIcon}>💧</Text>
            <View style={[styles.statusBadge, {
              backgroundColor: spo2Status === "Normal" ? "#E3F2FD" : "#FFF3E0"
            }]}>
              <Text style={[styles.statusBadgeText, {
                color: spo2Status === "Normal" ? BLUE : "#BA7517"
              }]}>{spo2Status.toUpperCase()}</Text>
            </View>
          </View>
          <Text style={styles.measurementLabel}>SpO2</Text>
          <Text style={styles.measurementValue}>
            {result.spo2}
            <Text style={styles.measurementUnit}> %</Text>
          </Text>
          <Text style={styles.measurementSub}>Normal range: 95–100%</Text>
        </View>
      </View>

      {/* Condition Classification Card */}
      <View style={[styles.conditionCard, { borderLeftColor: conditionColor }]}>
        <View style={styles.conditionCardTop}>
          <Text style={[styles.conditionLabel, { color: conditionColor }]}>
            {conditionIcon} {result.condition}
          </Text>
          <View style={[styles.confidenceBadge, { backgroundColor: conditionColor }]}>
            <Text style={styles.confidenceBadgeText}>
              {confidenceNum.toFixed(1)}% confidence
            </Text>
          </View>
        </View>
        <Text style={styles.conditionSub}>
          Recorded while: {result.pre_scan_state}
        </Text>
      </View>

      {/* AI Recommendation Card */}
      <View style={styles.recommendationCard}>
        <View style={styles.recommendationHeader}>
          <Text style={styles.recommendationIcon}>🛡</Text>
          <Text style={styles.recommendationTitle}>Medical Insight</Text>
        </View>
        <Text style={styles.recommendationText}>{result.recommendation}</Text>
      </View>

      {/* Action Buttons */}
      <TouchableOpacity style={styles.primaryButton} onPress={() => router.replace("/(tabs)")}>
        <Text style={styles.primaryButtonText}>Save & Finish</Text>
      </TouchableOpacity>

      <View style={styles.secondaryButtonRow}>
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => router.push("/(tabs)/history" as any)}
        >
          <Text style={styles.secondaryButtonText}>📋 History</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.secondaryButton} onPress={handleShare}>
          <Text style={styles.secondaryButtonText}>↗ Share</Text>
        </TouchableOpacity>
      </View>

      {/* Disclaimer */}
      <Text style={styles.disclaimer}>
        CardioApp is a tracking tool and does not replace professional medical
        diagnosis. Please consult a doctor if you feel unwell.
      </Text>

    </ScrollView>
  );
}

const BLUE = "#1565C0";

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  scrollContent: { paddingBottom: 40 },

  header: {
    backgroundColor: "#fff",
    paddingTop: 56,
    paddingBottom: 12,
    paddingHorizontal: 20,
    borderBottomWidth: 0.5,
    borderBottomColor: "#ddd",
    alignItems: "center",
  },
  headerTitle: { fontSize: 17, fontWeight: "600", color: "#111" },

  heroSection: { alignItems: "center", marginTop: 24, marginBottom: 12 },
  heroIcon: {
    width: 80, height: 80, borderRadius: 40,
    borderWidth: 2, justifyContent: "center", alignItems: "center",
    backgroundColor: "#fff",
  },
  heroIconText: { fontSize: 36 },

  analysisBadge: { alignItems: "center", marginBottom: 20 },
  analysisBadgeText: { fontSize: 18, fontWeight: "700", color: "#111", marginBottom: 4 },
  analysisBadgeSub: { fontSize: 12, color: "#888" },

  measurementRow: { flexDirection: "row", marginHorizontal: 16, gap: 10, marginBottom: 12 },
  measurementCard: {
    flex: 1, backgroundColor: "#fff", borderRadius: 12,
    padding: 12, borderWidth: 0.5, borderColor: "#ddd",
  },
  measurementCardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  measurementIcon: { fontSize: 20 },
  statusBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  statusBadgeText: { fontSize: 9, fontWeight: "700" },
  measurementLabel: { fontSize: 11, color: "#888", marginBottom: 2 },
  measurementValue: { fontSize: 28, fontWeight: "700", color: "#111" },
  measurementUnit: { fontSize: 13, fontWeight: "400", color: "#888" },
  measurementSub: { fontSize: 10, color: "#aaa", marginTop: 4 },

  conditionCard: {
    marginHorizontal: 16, backgroundColor: "#fff",
    borderRadius: 12, padding: 14, borderLeftWidth: 4,
    marginBottom: 12, borderWidth: 0.5, borderColor: "#ddd",
  },
  conditionCardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  conditionLabel: { fontSize: 16, fontWeight: "700" },
  confidenceBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 20 },
  confidenceBadgeText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  conditionSub: { fontSize: 12, color: "#888" },

  recommendationCard: {
    marginHorizontal: 16, backgroundColor: BLUE,
    borderRadius: 12, padding: 16, marginBottom: 20,
  },
  recommendationHeader: { flexDirection: "row", alignItems: "center", marginBottom: 8, gap: 6 },
  recommendationIcon: { fontSize: 16 },
  recommendationTitle: { fontSize: 14, fontWeight: "700", color: "#fff" },
  recommendationText: { fontSize: 13, color: "rgba(255,255,255,0.9)", lineHeight: 20 },

  primaryButton: {
    marginHorizontal: 16, backgroundColor: BLUE,
    borderRadius: 30, height: 52, justifyContent: "center",
    alignItems: "center", marginBottom: 10,
  },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },

  secondaryButtonRow: { flexDirection: "row", marginHorizontal: 16, gap: 10, marginBottom: 16 },
  secondaryButton: {
    flex: 1, backgroundColor: "#fff", borderRadius: 10,
    height: 44, justifyContent: "center", alignItems: "center",
    borderWidth: 0.5, borderColor: "#ddd",
  },
  secondaryButtonText: { fontSize: 14, color: "#333", fontWeight: "500" },

  disclaimer: {
    marginHorizontal: 16, fontSize: 11, color: "#aaa",
    textAlign: "center", lineHeight: 16,
  },
});