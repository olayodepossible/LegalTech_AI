import type { ChatAttachment } from "@/types/app";

const REPLIES: Record<string, string> = {
  en: "Thanks for your question. In a production app, this would call your LegalTech RAG backend. For now, here is a placeholder analysis in English.",
  es: "Gracias por tu consulta. En producción, esto se conectaría a tu backend LegalTech. Por ahora, análisis de ejemplo en español.",
  fr: "Merci pour votre question. En production, cela appellerait votre backend LegalTech. Pour l’instant, voici une réponse d’exemple en français.",
  de: "Vielen Dank für Ihre Frage. In der Produktion würde dies Ihr LegalTech-Backend aufrufen. Hier eine Beispielantwort auf Deutsch.",
  ar: "شكرًا على سؤالك. في الإنتاج سيتم الاتصال بالخادم الخاص بك. هذه إجابة تجريبية بالعربية.",
  pt: "Obrigado pela sua pergunta. Em produção, isso chamaria o backend LegalTech. Resposta de exemplo em português.",
  zh: "感谢您的提问。生产环境中将连接您的 LegalTech 后端。此为中文示例回复。",
};

export function mockAssistantReply(
  userText: string,
  languageCode: string,
  attachments: ChatAttachment[],
): string {
  const base =
    REPLIES[languageCode] ??
    REPLIES.en.replace("English", languageCode.toUpperCase());
  const doc =
    attachments.length > 0
      ? ` I see ${attachments.length} attachment(s): ${attachments.map((a) => a.name).join(", ")}.`
      : "";
  const snippet =
    userText.length > 120 ? `${userText.slice(0, 120)}…` : userText;
  return `${base}\n\nYou asked: “${snippet}”.${doc}`;
}
