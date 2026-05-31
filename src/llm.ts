export interface OllamaOptions {
  model?: string;
  timeoutMs?: number;
}

export async function generateResponse(
  prompt: string,
  options: OllamaOptions = {}
): Promise<string> {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 120000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch("http://127.0.0.1:11434/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: options.model ?? "phi",
        prompt,
        stream: false,
        options: {
          temperature: 0.2,
          num_ctx: 2048
        }
      }),
      signal: controller.signal
    });

    if (!response.ok) {
      throw new Error(`Ollama returned HTTP ${response.status}`);
    }

    const data = (await response.json()) as { response?: string; error?: string };
    if (data.error) {
      throw new Error(data.error);
    }
    if (!data.response || !data.response.trim()) {
      throw new Error("Invalid response from model");
    }

    return data.response.trim();
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Model is slow (likely first run or large input). Try again or use smaller file.");
    }

    if (error instanceof TypeError) {
      throw new Error("AI server not running (ollama serve)");
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
