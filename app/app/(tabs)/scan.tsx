import {
  View,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useState, useEffect, useRef } from "react";
import { CameraView, useCameraPermissions, useMicrophonePermissions } from "expo-camera"
import { FLASK_URL, getAuthToken } from "@/constants/api";
import { Text } from "@/components/AppText";

const SCAN_DURATION = 30;

export default function ScanScreen() {
  const router = useRouter();
  const { pre_scan_state } = useLocalSearchParams<{ pre_scan_state?: string }>();
  const [permission, requestPermission] = useCameraPermissions();
  const [micPermission, requestMicPermission] = useMicrophonePermissions();
  const [isScanning, setIsScanning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const cameraRef = useRef<CameraView>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!permission?.granted) requestPermission();
    if (!micPermission?.granted) requestMicPermission();
  }, []);

  useEffect(() => {
    if (isScanning) {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => {
          if (prev >= SCAN_DURATION) {
            handleStopScan();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isScanning]);

  const handleStartScan = async () => {
    if (!cameraRef.current) return;
    setElapsed(0);
    setIsScanning(true);

    // Wait for camera to fully initialize before recording
    await new Promise(resolve => setTimeout(resolve, 500));

    cameraRef.current.recordAsync({
      maxDuration: SCAN_DURATION,
    }).then((video) => {
      if (video?.uri) {
        sendVideoToFlask(video.uri);
      }
    }).catch((err) => {
      console.log("Recording error:", err);
    });
  }; // <-- handleStartScan ends here

  const handleStopScan = () => {
    setIsScanning(false);
    setElapsed(0);
    if (cameraRef.current) {
      cameraRef.current.stopRecording();
    }
  };

  const sendVideoToFlask = async (videoUri: string) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append("video", {
        uri: videoUri,
        type: "video/mp4",
        name: "scan.mp4",
      } as any);
      formData.append("pre_scan_state", pre_scan_state ?? "Resting");

      const token = await getAuthToken();
      const response = await fetch(`${FLASK_URL}/scan/predict-video`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        Alert.alert("Error", result.message || "Something went wrong");
        return;
      }

      router.push({
        pathname: "/(tabs)/results",
        params: {
          condition: result.condition,
          confidence: String(result.confidence),
          heart_rate: String(result.heart_rate),
          spo2: String(result.spo2),
          pre_scan_state: result.pre_scan_state,
          scan_id: String(result.scan_id),
          recommendation: result.recommendation,
          scanned_at: new Date().toLocaleString(),
          basis: String(result.basis ?? ""),
          regularity: String(result.regularity ?? ""),
          prv: String(result.prv_ms ?? ""),
          quality: String(result.quality ?? ""),
        },
      });

    } catch (error) {
      Alert.alert("Connection Error", "Could not reach the server. Make sure Flask is running.");
      console.log("Fetch error:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    if (isScanning && cameraRef.current) {
      cameraRef.current.stopRecording();
    }
    setIsScanning(false);
    setElapsed(0);
    router.back();
  };

  const progress = elapsed / SCAN_DURATION;
  const progressPercent = Math.round(progress * 100);
  const secondsRemaining = SCAN_DURATION - elapsed;

  if (!permission?.granted) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionTitle}>Camera Access Required</Text>
        <Text style={styles.permissionSub}>
          CardioApp needs your camera to capture PPG signals from your fingertip.
        </Text>
        <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={handleCancel} style={styles.backButton}>
          <Text style={styles.backText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {isProcessing ? "Processing..." : "Live Scan"}
        </Text>
        <View style={{ width: 60 }} />
      </View>

      <View style={styles.bpmCircle}>
        <Text style={styles.bpmValue}>{isScanning ? "..." : "--"}</Text>
        <Text style={styles.bpmLabel}>BPM</Text>
      </View>

      <Text style={styles.pulseLabel}>
        {isProcessing
          ? "Analysing signal..."
          : isScanning
          ? "∿  Capturing Pulse Wave..."
          : "Press Start Scan to begin"}
      </Text>

      <View style={styles.cameraCard}>
        <View style={styles.cameraProperTag}>
          <Text style={styles.cameraProperText}>ℹ  Proper Alignment</Text>
        </View>
        <CameraView
          ref={cameraRef}
          style={StyleSheet.absoluteFill}
          facing="back"
          mode="video"
          videoQuality="480p"
          enableTorch={isScanning}
        />
        <View style={styles.cameraOverlay}>
          <Text style={styles.cameraOverlayText}>
            Place your finger firmly over the camera lens and flash
          </Text>
        </View>
      </View>

      <View style={styles.progressSection}>
        <View style={styles.progressLabelRow}>
          <Text style={styles.progressTitle}>Scan Progress</Text>
          <Text style={styles.progressPercent}>
            {isScanning ? `${progressPercent}%` : "0%"}
          </Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progressPercent}%` }]} />
        </View>
        {isScanning && (
          <Text style={styles.progressSub}>{secondsRemaining}s remaining</Text>
        )}
      </View>

      <View style={styles.indicatorRow}>
        <View style={styles.indicatorCard}>
          <Text style={styles.indicatorIcon}>💡</Text>
          <Text style={styles.indicatorLabel}>Light Level</Text>
          <Text style={styles.indicatorValue}>{isScanning ? "Optimal" : "--"}</Text>
        </View>
        <View style={styles.indicatorCard}>
          <Text style={styles.indicatorIcon}>⚖️</Text>
          <Text style={styles.indicatorLabel}>Stability</Text>
          <Text style={styles.indicatorValue}>{isScanning ? "Steady" : "--"}</Text>
        </View>
      </View>

      <View style={styles.buttonRow}>
        {isProcessing ? (
          <View style={styles.processingButton}>
            <Text style={styles.processingButtonText}>Analysing...</Text>
          </View>
        ) : !isScanning ? (
          <TouchableOpacity style={styles.startButton} onPress={handleStartScan}>
            <Text style={styles.startButtonText}>Start Scan</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.stopButton} onPress={handleStopScan}>
            <Text style={styles.stopButtonText}>✕  Stop Scan</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const BLUE = "#1565C0";

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  permissionContainer: { flex: 1, justifyContent: "center", alignItems: "center", padding: 32, backgroundColor: "#f5f5f5" },
  permissionTitle: { fontSize: 20, fontWeight: "700", color: "#111", marginBottom: 12, textAlign: "center" },
  permissionSub: { fontSize: 14, color: "#666", textAlign: "center", lineHeight: 22, marginBottom: 24 },
  permissionButton: { backgroundColor: BLUE, paddingVertical: 14, paddingHorizontal: 32, borderRadius: 30 },
  permissionButtonText: { color: "#fff", fontSize: 15, fontWeight: "700" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 56, paddingHorizontal: 20, paddingBottom: 12, backgroundColor: "#fff", borderBottomWidth: 0.5, borderBottomColor: "#ddd" },
  backButton: { width: 60 },
  backText: { fontSize: 17, color: BLUE },
  headerTitle: { fontSize: 17, fontWeight: "600", color: "#111" },
  bpmCircle: { width: 120, height: 120, borderRadius: 60, borderWidth: 3, borderColor: BLUE, justifyContent: "center", alignItems: "center", alignSelf: "center", marginTop: 20, backgroundColor: "#fff" },
  bpmValue: { fontSize: 36, fontWeight: "700", color: BLUE },
  bpmLabel: { fontSize: 12, color: "#888", marginTop: 2 },
  pulseLabel: { textAlign: "center", fontSize: 13, color: BLUE, marginTop: 10, marginBottom: 14 },
  cameraCard: { marginHorizontal: 20, borderRadius: 12, overflow: "hidden", backgroundColor: "#000", height: 160 },
  cameraProperTag: { position: "absolute", top: 10, left: 10, zIndex: 10, backgroundColor: "rgba(255,255,255,0.85)", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  cameraProperText: { fontSize: 11, color: "#333" },
  cameraOverlay: { position: "absolute", bottom: 0, left: 0, right: 0, backgroundColor: "rgba(0,0,0,0.5)", padding: 8, zIndex: 10 },
  cameraOverlayText: { color: "#fff", fontSize: 11, textAlign: "center" },
  progressSection: { marginHorizontal: 20, marginTop: 16 },
  progressLabelRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  progressTitle: { fontSize: 13, fontWeight: "600", color: "#333" },
  progressPercent: { fontSize: 13, fontWeight: "600", color: BLUE },
  progressTrack: { height: 6, backgroundColor: "#ddd", borderRadius: 4, overflow: "hidden" },
  progressFill: { height: "100%", backgroundColor: BLUE, borderRadius: 4 },
  progressSub: { fontSize: 11, color: "#888", marginTop: 4 },
  indicatorRow: { flexDirection: "row", marginHorizontal: 20, marginTop: 12, gap: 10 },
  indicatorCard: { flex: 1, backgroundColor: "#fff", borderRadius: 10, padding: 10, alignItems: "center", borderWidth: 0.5, borderColor: "#ddd" },
  indicatorIcon: { fontSize: 18, marginBottom: 2 },
  indicatorLabel: { fontSize: 10, color: "#888" },
  indicatorValue: { fontSize: 13, fontWeight: "600", color: "#333", marginTop: 2 },
  buttonRow: { marginHorizontal: 20, marginTop: 16 },
  startButton: { backgroundColor: BLUE, borderRadius: 30, height: 52, justifyContent: "center", alignItems: "center" },
  startButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  stopButton: { backgroundColor: "#fff", borderRadius: 30, height: 52, justifyContent: "center", alignItems: "center", borderWidth: 1, borderColor: "#E24B4A" },
  stopButtonText: { color: "#E24B4A", fontSize: 16, fontWeight: "700" },
  processingButton: { backgroundColor: "#ddd", borderRadius: 30, height: 52, justifyContent: "center", alignItems: "center" },
  processingButtonText: { color: "#888", fontSize: 16, fontWeight: "700" },
});