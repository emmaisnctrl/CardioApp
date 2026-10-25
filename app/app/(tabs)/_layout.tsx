import { Tabs } from 'expo-router';
import React from 'react';

import { HapticTab } from '@/components/haptic-tab';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        tabBarStyle: { display: "flex" },
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="house.fill" color={color} />,
        }}
      />
      <Tabs.Screen
        name="scan"
        options={{
          title: 'Scan',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="heart.fill" color={color} />,
          href: null,
        }}
      />

      <Tabs.Screen
        name="results"
        options={{
          title: 'Results',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="heart.text.square.fill" color={color} />,
        }}
      />

      <Tabs.Screen
        name="prescan"
        options={{
          title: 'Pre-scan',
          href: null, // hidden from tab bar
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="heart.fill" color={color} />,
        }}
      />
    
    </Tabs>
  );
}