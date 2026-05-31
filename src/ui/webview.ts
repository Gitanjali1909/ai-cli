import * as vscode from "vscode";

export function showResultPanel(title: string, result: string): void {
  const panel = vscode.window.createWebviewPanel(
    "aiCliJudgeResult",
    title,
    vscode.ViewColumn.Beside,
    {
      enableScripts: false,
      retainContextWhenHidden: true
    }
  );

  panel.webview.html = renderHtml(title, result);
}

function renderHtml(title: string, result: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: var(--vscode-font-family);
      color: var(--vscode-editor-foreground);
      background: var(--vscode-editor-background);
      line-height: 1.55;
      padding: 24px;
    }
    h1 {
      color: var(--vscode-textLink-foreground);
      font-size: 20px;
      margin: 0 0 20px;
    }
    h2 {
      color: var(--vscode-textLink-foreground);
      border-bottom: 1px solid var(--vscode-panel-border);
      font-size: 15px;
      margin: 24px 0 8px;
      padding-bottom: 6px;
    }
    pre {
      background: var(--vscode-textCodeBlock-background);
      border-radius: 6px;
      overflow-x: auto;
      padding: 12px;
    }
    code {
      font-family: var(--vscode-editor-font-family);
    }
    .content {
      max-width: 920px;
    }
  </style>
</head>
<body>
  <main class="content">
    <h1>${escapeHtml(title)}</h1>
    ${formatSections(result)}
  </main>
</body>
</html>`;
}

function formatSections(text: string): string {
  const lines = text.split(/\r?\n/);
  const html: string[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
      }
      inCodeBlock = !inCodeBlock;
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(rawLine);
      continue;
    }

    const heading = normalizeHeading(line);
    if (heading) {
      html.push(`<h2>${escapeHtml(heading)}</h2>`);
      continue;
    }

    if (!line.trim()) {
      html.push("<br>");
      continue;
    }

    html.push(`<p>${escapeHtml(line)}</p>`);
  }

  if (codeLines.length) {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }

  return html.join("\n");
}

function normalizeHeading(line: string): string | null {
  const cleaned = line.replace(/^\d+[\).]\s*/, "").replace(/[:#*_]/g, "").trim();
  const headings = ["Overview", "Issues", "Suggestions", "Improved Code"];
  return headings.includes(cleaned) ? cleaned : null;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
