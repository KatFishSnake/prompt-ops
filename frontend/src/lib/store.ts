import { create } from "zustand";

interface AppState {
  onboarded: boolean;
  setOnboarded: (v: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  onboarded:
    typeof window !== "undefined" ? localStorage.getItem("promptops-onboarded") === "true" : true,
  setOnboarded: (v) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("promptops-onboarded", String(v));
    }
    set({ onboarded: v });
  },
}));
