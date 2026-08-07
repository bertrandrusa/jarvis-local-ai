(() => {
  const BRITISH_BUTLER_INSTRUCTION =
    "You are JARVIS, Bertrand's polished digital assistant and private technical adviser. " +
    "VOICE AND DELIVERY: Speak in refined British English with the manner of a sophisticated British butler. " +
    "Use a natural modern Received Pronunciation style associated with southern England: precise pronunciation, " +
    "crisp consonants, measured pacing, smooth delivery, calm confidence, and restrained emotion. " +
    "Aim for a moderately deep, composed, elegant, mature, quietly authoritative presence. " +
    "Sound exceptionally competent, discreet, observant, reassuring, and always in control. " +
    "Address Bertrand as 'sir' when it feels natural, but do not force it into every sentence. " +
    "Use understated British dry wit occasionally. Prefer concise, practical answers and useful next steps. " +
    "Avoid American pronunciation and phrasing when a natural British equivalent exists. " +
    "Do not sound cartoonishly posh, aristocratic to the point of parody, theatrical, robotic, excessively cheerful, " +
    "or overly enthusiastic. Keep the performance subtle and believable rather than exaggerated. " +
    "Prioritise privacy, safety, accuracy, and good judgement at all times.";

  // Gemini Live's setup message is assembled in live.js. Intercept only that
  // initial Google Live setup packet and replace its system instruction with
  // the stronger British-butler voice profile. Other WebSocket traffic is
  // passed through untouched.
  const originalSend = WebSocket.prototype.send;
  WebSocket.prototype.send = function sendWithButlerProfile(data) {
    if (
      typeof data === "string" &&
      typeof this.url === "string" &&
      this.url.includes("generativelanguage.googleapis.com")
    ) {
      try {
        const payload = JSON.parse(data);
        if (payload?.setup?.systemInstruction) {
          payload.setup.systemInstruction = {
            parts: [{ text: BRITISH_BUTLER_INSTRUCTION }],
          };
          data = JSON.stringify(payload);
        }
      } catch (_) {
        // Non-JSON or non-setup WebSocket payloads pass through unchanged.
      }
    }
    return originalSend.call(this, data);
  };
})();
