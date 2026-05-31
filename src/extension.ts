import * as vscode from "vscode";

import { generateResponse } from "./llm";
import { AiTask, buildPrompt } from "./prompt";
import { showResultPanel } from "./ui/webview";

export function activate(context: vscode.ExtensionContext): void {
  const statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusItem.text = "$(sparkle) AI Judge";
  statusItem.tooltip = "Select code for better results";
  statusItem.command = "aiCliJudge.explainCode";
  statusItem.show();

  context.subscriptions.push(
    statusItem,
    vscode.commands.registerCommand("aiCliJudge.explainCode", () => runAiTask("explain")),
    vscode.commands.registerCommand("aiCliJudge.fixCode", () => runAiTask("fix")),
    vscode.commands.registerCommand("aiCliJudge.reviewCode", () => runAiTask("review")),
    vscode.commands.registerCommand("aiCliJudge.toggleJudgeMode", toggleJudgeMode)
  );
}

export function deactivate(): void {
  // Nothing to dispose manually.
}

async function runAiTask(task: AiTask): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("Open a file before running AI CLI Judge.");
    return;
  }

  const code = getSelectedOrFullText(editor);
  if (!code.trim()) {
    vscode.window.showWarningMessage("No code found in the active editor.");
    return;
  }

  const config = vscode.workspace.getConfiguration("aiCliJudge");
  const judgeEnabled = config.get<boolean>("judgeMode", true);
  const model = config.get<string>("model", "phi");
  const timeoutMs = config.get<number>("timeoutMs", 120000);
  const prompt = buildPrompt(task, buildSmartContext(code), judgeEnabled);

  try {
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `AI CLI Judge: ${titleForTask(task)}`,
        cancellable: false
      },
      async () => {
        const result = await generateResponse(prompt, { model, timeoutMs });
        showResultPanel(`AI CLI: ${titleForTask(task)}`, result);
      }
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    vscode.window.showErrorMessage(message);
  }
}

function getSelectedOrFullText(editor: vscode.TextEditor): string {
  const selection = editor.selection;
  if (!selection.isEmpty) {
    return editor.document.getText(selection);
  }

  return editor.document.getText();
}

function chunkCode(code: string, chunkSize = 6000): string[] {
  const chunks: string[] = [];
  for (let index = 0; index < code.length; index += chunkSize) {
    chunks.push(code.slice(index, index + chunkSize));
  }
  return chunks;
}

function buildSmartContext(code: string): string {
  const cleaned = removeEmptyAndCommentLines(code);
  const lines = cleaned.split(/\r?\n/);
  const structuredContext =
    lines.length <= 400
      ? cleaned
      : [
          ...lines.slice(0, 200),
          "",
          "[middle section omitted due to size]",
          "",
          ...lines.slice(-100)
        ].join("\n");

  if (structuredContext.length < 8000) {
    return structuredContext;
  }

  const [firstChunk] = chunkCode(structuredContext);
  return `This is part 1 of a larger file. Focus only on given code.\n\n${firstChunk}`;
}

function removeEmptyAndCommentLines(code: string): string {
  return code
    .split(/\r?\n/)
    .filter((line) => {
      const trimmed = line.trim();
      return trimmed && !trimmed.startsWith("#") && !trimmed.startsWith("//");
    })
    .join("\n");
}

function titleForTask(task: AiTask): string {
  if (task === "explain") {
    return "Explain Code";
  }
  if (task === "fix") {
    return "Fix Code";
  }
  return "Review Code";
}

async function toggleJudgeMode(): Promise<void> {
  const config = vscode.workspace.getConfiguration("aiCliJudge");
  const currentValue = config.get<boolean>("judgeMode", true);
  const nextValue = !currentValue;

  await config.update("judgeMode", nextValue, vscode.ConfigurationTarget.Global);
  vscode.window.showInformationMessage(`AI CLI Judge Mode ${nextValue ? "ON" : "OFF"}`);
}
