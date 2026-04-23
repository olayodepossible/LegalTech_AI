export const RESPONSE_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "pt", label: "Português" },
] as const;

export function languageLabel(code: string): string {
  return RESPONSE_LANGUAGES.find((l) => l.code === code)?.label ?? code;
}
