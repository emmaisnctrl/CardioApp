import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { useState } from "react";

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* PPG Wave Header */}
        <View style={styles.header}>
          <View style={styles.waveContainer}>
            <Text style={styles.waveLine}>〜∿〜</Text>
          </View>
        </View>

        {/* Form Card */}
        <View style={styles.card}>
          {/* App Name */}
          <Text style={styles.appName}>CardioApp</Text>
          <Text style={styles.appTagline}>
            Clinical heart health monitoring at your fingertips.
          </Text>
        </View>

        {/* Welcome */}
        <View style={styles.formSection}>
          <Text style={styles.welcomeHeading}>Welcome Back</Text>
          <Text style={styles.welcomeSub}>
            Sign in to access your health data.
          </Text>

          {/* Email */}
          <Text style={styles.label}>Email Address</Text>
          <View style={styles.inputWrapper}>
            <Text style={styles.inputIcon}>✉</Text>
            <TextInput
              style={styles.input}
              placeholder="doctor@example.com"
              placeholderTextColor="#aaa"
              keyboardType="email-address"
              autoCapitalize="none"
              value={email}
              onChangeText={setEmail}
            />
          </View>

          {/* Password */}
          <View style={styles.passwordLabelRow}>
            <Text style={styles.label}>Password</Text>
            <TouchableOpacity
              onPress={() => router.push("/(auth)/forgot-password")}
            >
              <Text style={styles.forgotText}>Forgot?</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.inputWrapper}>
            <Text style={styles.inputIcon}>🔒</Text>
            <TextInput
              style={styles.input}
              placeholder="••••••••"
              placeholderTextColor="#aaa"
              secureTextEntry={!showPassword}
              value={password}
              onChangeText={setPassword}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
              <Text style={styles.inputIcon}>{showPassword ? "🙈" : "👁"}</Text>
            </TouchableOpacity>
          </View>
          {/* Login Button */}
          <TouchableOpacity
            style={styles.loginButton}
            onPress={() => router.replace("/(tabs)/explore")}
            activeOpacity={0.85}
          >
            <Text style={styles.loginButtonText}>Sign In</Text>
          </TouchableOpacity>

          {/* Divider */}
          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* Create Account */}
          <View style={styles.registerRow}>
            <Text style={styles.registerText}>Don't have an account? </Text>
            <TouchableOpacity onPress={() => router.push("/(auth)/register")}>
              <Text style={styles.registerLink}>Create New Account</Text>
            </TouchableOpacity>
          </View>

          {/* Terms */}
          <Text style={styles.terms}>
            By continuing, you agree to CardioApp's{" "}
            <Text style={styles.termsLink}>Terms of Service</Text> and{" "}
            <Text style={styles.termsLink}>Privacy Policy</Text>.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const BLUE = "#1565C0";
const LIGHT_BLUE = "#E3F2FD";

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  scrollContent: {
    flexGrow: 1,
  },

  // Header
  header: {
    backgroundColor: BLUE,
    height: 180,
    justifyContent: "center",
    alignItems: "center",
  },
  waveContainer: {
    justifyContent: "center",
    alignItems: "center",
  },
  waveLine: {
    fontSize: 48,
    color: "rgba(255,255,255,0.8)",
    letterSpacing: 4,
  },

  // Card
  card: {
    backgroundColor: "#fff",
    marginHorizontal: 24,
    marginTop: -32,
    borderRadius: 16,
    padding: 20,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  appName: {
    fontSize: 22,
    fontWeight: "700",
    color: BLUE,
    marginBottom: 4,
  },
  appTagline: {
    fontSize: 13,
    color: "#666",
    textAlign: "center",
    lineHeight: 18,
  },

  // Form
  formSection: {
    paddingHorizontal: 24,
    paddingTop: 28,
    paddingBottom: 32,
  },
  welcomeHeading: {
    fontSize: 26,
    fontWeight: "700",
    color: "#111",
    marginBottom: 4,
  },
  welcomeSub: {
    fontSize: 14,
    color: "#666",
    marginBottom: 24,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#333",
    marginBottom: 6,
  },
  passwordLabelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  forgotText: {
    fontSize: 13,
    color: BLUE,
    fontWeight: "500",
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    paddingHorizontal: 12,
    marginBottom: 16,
    height: 50,
  },
  inputIcon: {
    fontSize: 16,
    marginRight: 8,
    color: "#999",
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: "#111",
  },

  // Button
  loginButton: {
    backgroundColor: BLUE,
    borderRadius: 30,
    height: 52,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 4,
    marginBottom: 20,
  },
  loginButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.5,
  },

  // Divider
  dividerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 20,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: "#ddd",
  },
  dividerText: {
    marginHorizontal: 12,
    fontSize: 12,
    color: "#999",
  },

  // Register
  registerRow: {
    flexDirection: "row",
    justifyContent: "center",
    marginBottom: 20,
  },
  registerText: {
    fontSize: 14,
    color: "#555",
  },
  registerLink: {
    fontSize: 14,
    color: BLUE,
    fontWeight: "700",
  },

  // Terms
  terms: {
    fontSize: 11,
    color: "#aaa",
    textAlign: "center",
    lineHeight: 16,
  },
  termsLink: {
    color: "#888",
    textDecorationLine: "underline",
  },
});