import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { useState } from "react";

const STATES = [
  {
    id: "Resting",
    icon: "💆",
    title: "Resting",
    description: "You have been seated or lying down for 5+ minutes.",
  },
  {
    id: "Active",
    icon: "🏃‍➡️",
    title: "Active / Post-Exercise",
    description: "Just finished physical activity or moving around.",
  },
  {
    id: "Unwell",
    icon: "🌡",
    title: "Feeling Unwell",
    description: "Experiencing fatigue, stress, or minor symptoms.",
  },
];

export default function PreScanScreen() {
  const router = useRouter();
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState(false);

  const handleBeginScan = () => {
    if (!selected) {
      setError(true);
      return;
    }
    router.push({
      pathname: "/(tabs)/scan",
      params: { pre_scan_state: selected },
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Prepare for scan</Text>
        <View style={{ width: 60 }} />
      </View>

      {/* Illustration area */}
      <View style={styles.illustrationBox}>
        <Text style={styles.illustrationIcon}>🫀</Text>
        <Text style={styles.illustrationTitle}>Scan preparation</Text>
        <Text style={styles.illustrationSub}>
          To ensure the best results, please follow these steps before starting your scan.
        </Text>
      </View>

      {/* Tips */}
      <View style={styles.tipsCard}>
        <Text style={styles.tipItem}>• Sit comfortably in a quiet environment</Text>
        <Text style={styles.tipItem}>• Keep your hands warm and still</Text>
        <Text style={styles.tipItem}>• Ensure the camera lens is clean</Text>
      </View>

      {/* State selector */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Current state</Text>
        {error && <Text style={styles.errorText}>Please select one</Text>}
      </View>

      {STATES.map((state) => (
        <TouchableOpacity
          key={state.id}
          style={[
            styles.stateCard,
            selected === state.id && styles.stateCardSelected,
          ]}
          onPress={() => {
            setSelected(state.id);
            setError(false);
          }}
          activeOpacity={0.8}
        >
          <View style={[
            styles.stateIconContainer,
            selected === state.id && styles.stateIconContainerSelected,
          ]}>
            <Text style={styles.stateIcon}>{state.icon}</Text>
          </View>
          <View style={styles.stateInfo}>
            <Text style={[
              styles.stateTitle,
              selected === state.id && styles.stateTitleSelected,
            ]}>{state.title}</Text>
            <Text style={styles.stateDescription}>{state.description}</Text>
          </View>
          <View style={[
            styles.radio,
            selected === state.id && styles.radioSelected,
          ]} />
        </TouchableOpacity>
      ))}

      {/* Begin Scan Button */}
      <TouchableOpacity
        style={[styles.beginButton, !selected && styles.beginButtonDisabled]}
        onPress={handleBeginScan}
        activeOpacity={0.85}
      >
        <Text style={styles.beginButtonText}>Begin scan</Text>
      </TouchableOpacity>

      <Text style={styles.disclaimer}>
        By starting the scan, you agree to our privacy policy regarding health data processing.
      </Text>

    </ScrollView>
  );
}

const BLUE = "#1565C0";
const LIGHT_BLUE = "#E3F2FD";

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  scrollContent: { paddingBottom: 40 },

  header: {
    flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", backgroundColor: "#fff",
    paddingTop: 56, paddingHorizontal: 20, paddingBottom: 12,
    borderBottomWidth: 0.5, borderBottomColor: "#ddd",
  },
  backButton: { width: 60 },
  backText: { fontSize: 17, color: BLUE },
  headerTitle: { fontSize: 17, fontWeight: "600", color: "#111" },

  illustrationBox: {
    alignItems: "center", backgroundColor: "#fff",
    margin: 16, borderRadius: 12, padding: 24,
    borderWidth: 0.5, borderColor: "#ddd",
  },
  illustrationIcon: { fontSize: 48, marginBottom: 12 },
  illustrationTitle: { fontSize: 18, fontWeight: "700", color: "#111", marginBottom: 8 },
  illustrationSub: { fontSize: 13, color: "#666", textAlign: "center", lineHeight: 20 },

  tipsCard: {
    marginHorizontal: 16, backgroundColor: LIGHT_BLUE,
    borderRadius: 10, padding: 14, marginBottom: 20,
  },
  tipItem: { fontSize: 13, color: BLUE, marginBottom: 6, lineHeight: 20 },

  sectionHeader: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", marginHorizontal: 16, marginBottom: 10,
  },
  sectionTitle: { fontSize: 13, fontWeight: "600", color: "#555", textTransform: "uppercase", letterSpacing: 0.5 },
  errorText: { fontSize: 12, color: "#E24B4A" },

  stateCard: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "#fff", marginHorizontal: 16,
    borderRadius: 12, padding: 14, marginBottom: 10,
    borderWidth: 1, borderColor: "#ddd",
  },
  stateCardSelected: {
    borderColor: BLUE, backgroundColor: LIGHT_BLUE,
  },
  stateIconContainer: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: "#f0f0f0", justifyContent: "center",
    alignItems: "center", marginRight: 12,
  },
  stateIconContainerSelected: { backgroundColor: BLUE },
  stateIcon: { fontSize: 20 },
  stateInfo: { flex: 1 },
  stateTitle: { fontSize: 14, fontWeight: "600", color: "#111", marginBottom: 3 },
  stateTitleSelected: { color: BLUE },
  stateDescription: { fontSize: 12, color: "#888", lineHeight: 18 },
  radio: {
    width: 20, height: 20, borderRadius: 10,
    borderWidth: 1.5, borderColor: "#ccc",
  },
  radioSelected: { borderColor: BLUE, backgroundColor: BLUE },

  beginButton: {
    marginHorizontal: 16, marginTop: 20, backgroundColor: BLUE,
    borderRadius: 30, height: 52, justifyContent: "center", alignItems: "center",
  },
  beginButtonDisabled: { backgroundColor: "#aac4e8" },
  beginButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },

  disclaimer: {
    marginHorizontal: 16, marginTop: 12, fontSize: 11,
    color: "#aaa", textAlign: "center", lineHeight: 16,
  },
});