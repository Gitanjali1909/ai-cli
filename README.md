# AI CLI Judge

VS Code extension that sends the active editor selection or full file to local Ollama at `http://127.0.0.1:11434/api/generate`.

## Commands

- `AI CLI: Explain Code`
- `AI CLI: Fix Code`
- `AI CLI: Review Code`

## Setup

1. Start Ollama:

   ```powershell
   ollama serve
   ```

2. Make sure the default model exists:

   ```powershell
   ollama pull phi
   ```

3. Install dependencies and compile:

   ```powershell
   npm install
   npm run compile
   ```

4. Open this folder in VS Code and press `F5` to launch the Extension Development Host.

## Settings

- `aiCliJudge.judgeMode`: turns Amitabh Bachchan Senior Dev Judge Mode on or off.
- `aiCliJudge.model`: Ollama model name, default `phi`.
- `aiCliJudge.timeoutMs`: request timeout, default `120000`.
