import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from "react-native";
import { useRouter } from "expo-router";

// Mock data — replace with real data from AsyncStorage or API later
const MOCK_LAST_SCAN = {
  condition: "Normal",
  heart_rate: "76",
  spo2: "98",
  scanned_at: "Today, 9:41 AM",
};

export default function HomeScreen() {
  const router = useRouter();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>

      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Good morning</Text>
          <Text style={styles.greetingSub}>Ready for your daily scan?</Text>
        </View>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>C</Text>
        </View>
      </View>

      {/* Metric Cards */}
      <View style={styles.metricRow}>
        <View style={styles.metricCard}>
          <Text style={styles.metricIcon}>🫀</Text>
          <Text style={styles.metricValue}>{MOCK_LAST_SCAN.heart_rate}</Text>
          <Text style={styles.metricUnit}>BPM</Text>
          <Text style={styles.metricLabel}>Heart rate</Text>
        </View>
        <View style={styles.metricCard}>
          <Text style={styles.metricIcon}>💧</Text>
          <Text style={styles.metricValue}>{MOCK_LAST_SCAN.spo2}</Text>
          <Text style={styles.metricUnit}>%</Text>
          <Text style={styles.metricLabel}>Oxygen sat.</Text>
        </View>
      </View>

      {/* Begin Scan Button */}
      <TouchableOpacity
        style={styles.scanButton}
        onPress={() => router.push("/(tabs)/prescan" as any)}
        activeOpacity={0.85}
      >
        <Text style={styles.scanButtonText}>Begin new scan</Text>
      </TouchableOpacity>

      {/* Monthly Insights Banner */}
      <TouchableOpacity style={styles.insightsBanner} activeOpacity={0.85}>
        <View style={styles.insightsBannerLeft}>
          <Text style={styles.insightsBannerIcon}>📋</Text>
          <View>
            <Text style={styles.insightsBannerTitle}>Monthly health insights</Text>
            <Text style={styles.insightsBannerSub}>Available after 30 days of scans</Text>
          </View>
        </View>
        <Text style={styles.insightsBannerArrow}>›</Text>
      </TouchableOpacity>

      {/* Recent Scans */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Recent scans</Text>
        <TouchableOpacity>
          <Text style={styles.seeAll}>See all</Text>
        </TouchableOpacity>
      </View>

      {/* Mock scan entries */}
      {[
        { condition: "Normal", date: "Today, 9:41 AM", hr: "76", spo2: "98", state: "Resting", color: "#1D9E75" },
        { condition: "Normal", date: "Yesterday, 8:30 PM", hr: "72", spo2: "97", state: "Resting", color: "#1D9E75" },
        { condition: "Tachycardia", date: "2 days ago, 7:15 PM", hr: "112", spo2: "96", state: "Active", color: "#E24B4A" },
      ].map((scan, index) => (
        <TouchableOpacity
          key={index}
          style={styles.scanEntry}
          activeOpacity={0.7}
        >
          <View style={[styles.scanDot, { backgroundColor: scan.color }]} />
          <View style={styles.scanEntryInfo}>
            <Text style={styles.scanEntryCondition}>{scan.condition}</Text>
            <Text style={styles.scanEntryDate}>{scan.date} · {scan.state}</Text>
          </View>
          <View style={styles.scanEntryVitals}>
            <Text style={styles.scanEntryVital}>{scan.hr} BPM</Text>
            <Text style={styles.scanEntryVital}>{scan.spo2}% SpO2</Text>
          </View>
          <Text style={styles.scanEntryArrow}>›</Text>
        </TouchableOpacity>
      ))}

      {/* Tip card */}
      <View style={styles.tipCard}>
        <Text style={styles.tipIcon}>ℹ</Text>
        <Text style={styles.tipText}>
          Consistently scanning at the same time each day provides the most accurate trend data for wellness monitoring.
        </Text>
      </View>

    </ScrollView>
  );
}

const BLUE = "#1565C0";
const LIGHT_BLUE = "#E3F2FD";

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  scrollContent: { paddingBottom: 40 },

  header: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", backgroundColor: "#fff",
    paddingTop: 56, paddingHorizontal: 20, paddingBottom: 16,
    borderBottomWidth: 0.5, borderBottomColor: "#ddd",
  },
  greeting: { fontSize: 22, fontWeight: "700", color: "#111" },
  greetingSub: { fontSize: 13, color: "#888", marginTop: 2 },
  avatar: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: BLUE, justifyContent: "center", alignItems: "center",
  },
  avatarText: { color: "#fff", fontSize: 16, fontWeight: "700" },

  metricRow: { flexDirection: "row", margin: 16, gap: 12 },
  metricCard: {
    flex: 1, backgroundColor: "#fff", borderRadius: 12,
    padding: 14, borderWidth: 0.5, borderColor: "#ddd",
  },
  metricIcon: { fontSize: 20, marginBottom: 4 },
  metricValue: { fontSize: 28, fontWeight: "700", color: "#111" },
  metricUnit: { fontSize: 13, color: "#888" },
  metricLabel: { fontSize: 11, color: "#aaa", marginTop: 4, textTransform: "uppercase", letterSpacing: 0.5 },

  scanButton: {
    marginHorizontal: 16, backgroundColor: BLUE,
    borderRadius: 30, height: 56, flexDirection: "row",
    justifyContent: "center", alignItems: "center",
    gap: 8, marginBottom: 12,
  },
  scanButtonIcon: { color: "#fff", fontSize: 20 },
  scanButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },

  insightsBanner: {
    marginHorizontal: 16, backgroundColor: LIGHT_BLUE,
    borderRadius: 12, padding: 14, flexDirection: "row",
    justifyContent: "space-between", alignItems: "center",
    marginBottom: 20,
  },
  insightsBannerLeft: { flexDirection: "row", alignItems: "center", gap: 10 },
  insightsBannerIcon: { fontSize: 20 },
  insightsBannerTitle: { fontSize: 14, fontWeight: "600", color: BLUE },
  insightsBannerSub: { fontSize: 11, color: "#666", marginTop: 2 },
  insightsBannerArrow: { fontSize: 20, color: BLUE },

  sectionHeader: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", marginHorizontal: 16, marginBottom: 8,
  },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#111" },
  seeAll: { fontSize: 13, color: BLUE },

  scanEntry: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "#fff", marginHorizontal: 16,
    padding: 14, borderRadius: 10, marginBottom: 8,
    borderWidth: 0.5, borderColor: "#ddd",
  },
  scanDot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  scanEntryInfo: { flex: 1 },
  scanEntryCondition: { fontSize: 14, fontWeight: "600", color: "#111" },
  scanEntryDate: { fontSize: 11, color: "#888", marginTop: 2 },
  scanEntryVitals: { alignItems: "flex-end", marginRight: 8 },
  scanEntryVital: { fontSize: 11, color: "#555" },
  scanEntryArrow: { fontSize: 18, color: "#ccc" },

  tipCard: {
    flexDirection: "row", marginHorizontal: 16, marginTop: 8,
    backgroundColor: "#fff", borderRadius: 10, padding: 12,
    borderWidth: 0.5, borderColor: "#ddd", gap: 8, alignItems: "flex-start",
  },
  tipIcon: { fontSize: 16, marginTop: 1 },
  tipText: { flex: 1, fontSize: 12, color: "#888", lineHeight: 18 },
});