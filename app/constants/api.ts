import * as SecureStore from "expo-secure-store";

// One place to change the server address
export const FLASK_URL = "https://upcountry-haiku-saffron.ngrok-free.dev";

const AUTH_TOKEN_KEY = "cardioapp_auth_token";

export async function getAuthToken(): Promise<string | null> {
  try {
    const savedToken = await SecureStore.getItemAsync(AUTH_TOKEN_KEY);
    if (savedToken) {
      return savedToken;
    }

    const baseUrl = FLASK_URL.replace(/\/+$/, "");
    const res = await fetch(`${baseUrl}/auth/anonymous`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      console.log("Anonymous auth failed, status:", res.status);
      return null;
    }

    const data = await res.json();
    if (data.token) {
      await SecureStore.setItemAsync(AUTH_TOKEN_KEY, data.token);
      return data.token;
    }

    return null;
  } catch (error) {
    console.log("Error obtaining auth token:", error);
    return null;
  }
}
