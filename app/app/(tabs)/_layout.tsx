import { Tabs } from "expo-router";
import React from "react";
import { Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";

const BLUE = "#1565C0";
const INACTIVE = "#9AA3AE";

export default function TabLayout() {
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: BLUE,
        tabBarInactiveTintColor: INACTIVE,
        tabBarLabelStyle: {
          fontSize: 11,
          fontFamily: Platform.OS === "ios" ? undefined : "Inter_600SemiBold",
        },
        tabBarStyle: {
          backgroundColor: "#fff",
          borderTopWidth: 0,
          height: 58 + insets.bottom,
          paddingTop: 6,
          paddingBottom: Math.max(insets.bottom, 6),
          elevation: 12,
          shadowColor: "#0B2A4A",
          shadowOpacity: 0.08,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: -3 },
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "home" : "home-outline"} size={24} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="results"
        options={{
          title: "Results",
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "pulse" : "pulse-outline"} size={24} color={color} />
          ),
        }}
      />
      {/* Hidden from the bar; the bar is also hidden on these two screens */}
      <Tabs.Screen name="scan" options={{ href: null, tabBarStyle: { display: "none" } }} />
      <Tabs.Screen name="prescan" options={{ href: null, tabBarStyle: { display: "none" } }} />
    </Tabs>
  );
}