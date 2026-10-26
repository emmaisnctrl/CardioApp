import React from "react";
import { Platform, StyleSheet, Text as RNText, TextProps, TextStyle } from "react-native";

const FAMILY: Record<string, string> = {
  "400": "Inter_400Regular",
  "500": "Inter_500Medium",
  "600": "Inter_600SemiBold",
  "700": "Inter_700Bold",
  "800": "Inter_800ExtraBold",
};

export function Text({ style, ...props }: TextProps) {
  // On iPhones the system font already is San Francisco
  if (Platform.OS === "ios") return <RNText style={style} {...props} />;

  const flat = (StyleSheet.flatten(style) || {}) as TextStyle;
  let w = String(flat.fontWeight ?? "400");
  if (w === "normal") w = "400";
  if (w === "bold") w = "700";
  if (w === "900") w = "800";
  const fontFamily = FAMILY[w] ?? FAMILY["400"];

  return <RNText {...props} style={[style, { fontFamily, fontWeight: undefined }]} />;
}