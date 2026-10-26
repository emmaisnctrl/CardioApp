import { Platform, ViewStyle } from "react-native";

// One soft shadow reused by every card in the app
export const CARD_SHADOW = Platform.select({
  ios: {
    shadowColor: "#0B2A4A",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
  },
  android: {
    elevation: 3,
    shadowColor: "#0B2A4A",
  },
  default: {},
}) as ViewStyle;