import { defineStore } from "pinia";

interface ThemeState {
    useDarkMode: boolean | undefined;
}

export const useThemeStore = defineStore("theme", {
  state: (): ThemeState => {
    return {
        useDarkMode: undefined
    }
  }
});

export const updateThemeCss = (document: Document, useDarkMode?: boolean) => {
  const root_element = document.querySelector<HTMLElement>(':root');
  if (!root_element) { return; }

  if (!!useDarkMode) {
    root_element.classList.remove("light-mode");
        root_element.classList.add("dark-mode");
  } else {
    root_element.classList.remove("dark-mode");
    root_element.classList.add("light-mode");
  }
}