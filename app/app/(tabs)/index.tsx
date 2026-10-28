import {
  View,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Text } from "@/components/AppText";
import { CARD_SHADOW } from "@/constants/design";
import { FLASK_URL, getAuthToken } from "@/constants/api";

// Shape of a scan returned by Flask's /scan/history
interface SavedScan {
  id: number;
  heart_rate: number;
  spo2: number;
  condition: string;
  confidence_score: number;
  recommendation: string;
  pre_scan_state: string;
  pulse_regularity: string;
  prv_ms: number;
  scan_quality: string;
  scanned_at: string;
}

const CONDITION_COLORS: Record<string, string> = {
  Normal: "#1D9E75",
  Tachycardia: "#E24B4A",
  Bradycardia: "#BA7517",
  Inconclusive: "#BA7517",
  "Elevated (after activity)": "#BA7517",
};

// The server stores UTC time; convert it to the phone's local time
const toLocal = (s: string) => new Date(s.replace(" ", "T") + "Z");

// Greeting and sub-line based on the phone's clock
const timeOfDay = () => {
  const h = new Date().getHours();
  if (h >= 5 && h < 12)
    return { greeting: "Good morning", sub: "Ready for your morning scan?" };
  if (h >= 12 && h < 17)
    return { greeting: "Good afternoon", sub: "Ready for your afternoon scan?" };
  if (h >= 17 && h < 22)
    return { greeting: "Good evening", sub: "Ready for your evening scan?" };
  return { greeting: "Hello", sub: "A calm moment makes a better scan. Rest first, then scan." };
};

const formatWhen = (s: string) => {
  const d = toLocal(s);
  const now = new Date();
  const yesterday = new Date(now.getTime() - 86400000);
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (d.toDateString() === now.toDateString()) return `Today, ${time}`;
  if (d.toDateString() === yesterday.toDateString()) return `Yesterday, ${time}`;
  return `${d.toLocaleDateString([], { day: "numeric", month: "short" })}, ${time}`;
};

export default function HomeScreen() {
  const router = useRouter();
  const [scans, setScans] = useState<SavedScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Load the scan history from Flask
  const load = async () => {
    setLoading(true);
    setError(false);
    try {
      const token = await getAuthToken();
      const res = await fetch(`${FLASK_URL}/scan/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Bad response");
      const data = await res.json();
      setScans(data.scans ?? []);
    } catch (e) {
      console.log("History error:", e);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  // Reload every time the Home screen comes back into view
  useFocusEffect(
    useCallback(() => {
      load();
    }, [])
  );

  // Reopen a saved scan on the Results screen
  const openScan = (s: SavedScan) => {
    router.push({
      pathname: "/(tabs)/results",
      params: {
        condition: s.condition,
        confidence: s.confidence_score > 0 ? String(s.confidence_score) : "null",
        heart_rate: String(s.heart_rate),
        spo2: String(s.spo2),
        pre_scan_state: s.pre_scan_state || "Not recorded",
        regularity: s.pulse_regularity || "Not recorded",
        prv: String(s.prv_ms ?? 0),
        quality: s.scan_quality || "Not recorded",
        scan_id: String(s.id),
        recommendation: s.recommendation,
        scanned_at: toLocal(s.scanned_at).toLocaleString(),
      },
    });
  };

  const last = scans[0];
  const recent = scans.slice(0, 5);
  const { greeting, sub } = timeOfDay();

  // ── Resting trend, worked out from the saved scans ──────────
  // Only resting scans with usable signal quality count. Scans saved before
  // pulse analysis existed have no quality recorded, so they are left out.
  const usable = scans
    .filter(
      (s) =>
        s.pre_scan_state === "Resting" &&
        (s.scan_quality === "Good" || s.scan_quality === "Fair")
    )
    .slice(0, 5); // scans arrive newest first
  const n = usable.length;
  const avgHr = n > 0 ? usable.reduce((sum, s) => sum + s.heart_rate, 0) / n : 0;
  const highCount = usable.filter((s) => s.heart_rate > 105).length;
  const lowCount = usable.filter((s) => s.heart_rate < 55).length;
  const irregCount = usable.filter((s) => s.pulse_regularity === "Possibly irregular").length;
  const dayCount = new Set(usable.map((s) => toLocal(s.scanned_at).toDateString())).size;

  let trendText = "";
  let trendColor = BLUE;
  if (n < 3) {
    trendText = `Trends need at least 3 good resting scans. You have ${n} so far.`;
  } else if (highCount >= 3) {
    trendText = `${highCount} of your last ${n} resting scans were above the usual range. If this keeps happening on different days, consider a blood pressure check with a validated device and speak to a health professional.`;
    trendColor = AMBER;
  } else if (lowCount >= 3) {
    trendText = `${lowCount} of your last ${n} resting scans were below the usual range. This can be normal in active people, but speak to a health professional if you also feel dizzy, faint or unusually tired.`;
    trendColor = AMBER;
  } else if (irregCount >= 2) {
    trendText = `Pulse timing varied more than usual in ${irregCount} of your last ${n} resting scans. If this keeps appearing, ask a clinician whether an ECG is worthwhile.`;
    trendColor = AMBER;
  } else {
    trendText = `No concerning pattern in your last ${n} resting scans.`;
    trendColor = GREEN;
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>

      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>{greeting}</Text>
          <Text style={styles.greetingSub}>{sub}</Text>
        </View>
      </View>

      {/* Metric Cards (from the latest saved scan) */}
      <View style={styles.metricRow}>
        <View style={styles.metricCard}>
          <Text style={styles.metricIcon}>🫀</Text>
          <Text style={styles.metricValue}>
            {last ? last.heart_rate.toFixed(0) : "--"}
          </Text>
          <Text style={styles.metricUnit}>BPM</Text>
          <Text style={styles.metricLabel}>Last heart rate</Text>
        </View>
        <View style={styles.metricCard}>
          <Text style={styles.metricIcon}>📋</Text>
          <Text
            style={[
              styles.metricValueSmall,
              { color: last ? CONDITION_COLORS[last.condition] || "#111" : "#111" },
            ]}
          >
            {last ? last.condition : "--"}
          </Text>
          <Text style={styles.metricUnit}> </Text>
          <Text style={styles.metricLabel}>Last result</Text>
        </View>
      </View>

      {/* Begin Scan Button */}
      <TouchableOpacity
        style={styles.scanButton}
        onPress={() => router.push("/(tabs)/prescan" as any)}
        activeOpacity={0.85}
      >
        <Text style={styles.scanButtonIcon}></Text>
        <Text style={styles.scanButtonText}>Begin new scan</Text>
      </TouchableOpacity>

      {/* Resting trend */}
      {!loading && !error && (
        <View style={[styles.trendCard, { borderLeftColor: trendColor }]}>
          <Text style={styles.trendTitle}>Your resting trend</Text>
          <Text style={styles.trendText}>{trendText}</Text>
          {n >= 3 && (
            <Text style={styles.trendMeta}>
              {`Average resting heart rate ${avgHr.toFixed(0)} BPM over ${n} scans on ${dayCount} day${dayCount === 1 ? "" : "s"}.`}
              {dayCount < 2 ? " Trends are more meaningful across several days." : ""}
            </Text>
          )}
          <Text style={styles.trendMeta}>
            A pattern worth following up, not a diagnosis.
          </Text>
        </View>
      )}

      {/* Recent Scans */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Recent scans</Text>
      </View>

      {loading && <ActivityIndicator color={BLUE} style={{ marginTop: 16 }} />}

      {!loading && error && (
        <TouchableOpacity style={styles.messageCard} onPress={load}>
          <Text style={styles.messageText}>
            Could not load your scans. Check that Flask is running, then tap to retry.
          </Text>
        </TouchableOpacity>
      )}

      {!loading && !error && recent.length === 0 && (
        <View style={styles.messageCard}>
          <Text style={styles.messageText}>
            No scans yet. Tap "Begin new scan" to record your first one.
          </Text>
        </View>
      )}

      {!loading &&
        !error &&
        recent.map((scan) => (
          <TouchableOpacity
            key={scan.id}
            style={styles.scanEntry}
            activeOpacity={0.7}
            onPress={() => openScan(scan)}
          >
            <View
              style={[
                styles.scanDot,
                { backgroundColor: CONDITION_COLORS[scan.condition] || "#888" },
              ]}
            />
            <View style={styles.scanEntryInfo}>
              <Text style={styles.scanEntryCondition}>{scan.condition}</Text>
              <Text style={styles.scanEntryDate}>
                {formatWhen(scan.scanned_at)} · {scan.pre_scan_state || "Not recorded"}
              </Text>
            </View>
            <View style={styles.scanEntryVitals}>
              <Text style={styles.scanEntryVital}>
                {scan.heart_rate.toFixed(0)} BPM
              </Text>
            </View>
            <Text style={styles.scanEntryArrow}>›</Text>
          </TouchableOpacity>
        ))}

      {/* Disclaimer */}
      <Text style={styles.disclaimer}>
        CardioApp is a tracking tool and does not replace professional medical
        diagnosis. Please consult a doctor if you feel unwell.
      </Text>
    </ScrollView>
  );
}

const BLUE = "#1565C0";
const AMBER = "#BA7517";
const GREEN = "#1D9E75";
const CARD_BORDER = "#eef0f3";

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f6f8" },
  scrollContent: { paddingBottom: 40 },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fff",
    paddingTop: 56,
    paddingHorizontal: 20,
    paddingBottom: 16,
    borderBottomWidth: 0.5,
    borderBottomColor: "#ddd",
  },
  greeting: { fontSize: 26, fontWeight: "800", color: "#0B1B2B", letterSpacing: -0.3 },
  greetingSub: { fontSize: 13, color: "#7A8794", marginTop: 3 },

  metricRow: { flexDirection: "row", margin: 16, gap: 12 },
  metricCard: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    borderWidth: 0.5,
    borderColor: CARD_BORDER,
    ...CARD_SHADOW,
  },
  metricIcon: { fontSize: 20, marginBottom: 4 },
  metricValue: { fontSize: 28, fontWeight: "700", color: "#111" },
  metricValueSmall: { fontSize: 18, fontWeight: "700", marginTop: 6 },
  metricUnit: { fontSize: 13, color: "#888" },
  metricLabel: {
    fontSize: 11,
    color: "#aaa",
    marginTop: 4,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },

  scanButton: {
    marginHorizontal: 16,
    backgroundColor: BLUE,
    borderRadius: 30,
    height: 56,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    marginBottom: 16,
    elevation: 5,
    shadowColor: BLUE,
    shadowOpacity: 0.28,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  scanButtonIcon: { color: "#fff", fontSize: 20 },
  scanButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },

  trendCard: {
    marginHorizontal: 16,
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    borderLeftWidth: 4,
    marginBottom: 20,
    borderWidth: 0.5,
    borderColor: CARD_BORDER,
    ...CARD_SHADOW,
  },
  trendTitle: { fontSize: 14, fontWeight: "700", color: "#111", marginBottom: 4 },
  trendText: { fontSize: 13, color: "#444", lineHeight: 19 },
  trendMeta: { fontSize: 11, color: "#888", marginTop: 6, lineHeight: 16 },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginHorizontal: 16,
    marginBottom: 10,
  },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#111" },

  messageCard: {
    marginHorizontal: 16,
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    borderWidth: 0.5,
    borderColor: CARD_BORDER,
    ...CARD_SHADOW,
  },
  messageText: { fontSize: 13, color: "#666", lineHeight: 20, textAlign: "center" },

  scanEntry: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    marginHorizontal: 16,
    padding: 14,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 0.5,
    borderColor: CARD_BORDER,
    ...CARD_SHADOW,
  },
  scanDot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  scanEntryInfo: { flex: 1 },
  scanEntryCondition: { fontSize: 14, fontWeight: "600", color: "#111" },
  scanEntryDate: { fontSize: 11, color: "#888", marginTop: 2 },
  scanEntryVitals: { alignItems: "flex-end", marginRight: 8 },
  scanEntryVital: { fontSize: 12, color: "#555", fontWeight: "500" },
  scanEntryArrow: { fontSize: 18, color: "#ccc" },

  disclaimer: {
    marginHorizontal: 16,
    marginTop: 16,
    fontSize: 11,
    color: "#aaa",
    textAlign: "center",
    lineHeight: 16,
  },
});