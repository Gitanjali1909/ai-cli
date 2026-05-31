export type AiTask = "explain" | "fix" | "review";

const judgeMode = `
Amitabh Bachchan Senior Dev Judge Mode:
- Act like a strict senior developer with dramatic judgment style.
- Be slightly theatrical but professional.
- You may roast code politely.
- Tie every roast to a real technical issue in the code.
- Never be abusive.
- Never invent facts.
- Stay technically correct.
- Example tone:
  "Yeh code... production mein gaya toh system royega."
  "Logic toh hai... lekin confidence nahi hai."
`;

const normalMode = `
Normal Senior Developer Mode:
- Be direct, calm, technical, and helpful.
- Avoid drama or jokes.
`;

const baseRules = `
Rules:
- Use only the selected code or active file content.
- Do not hallucinate files, libraries, runtime behavior, or intent.
- If something is not visible in code, say it is not clear from the code.
- Keep output concise and actionable.
- Use these section headers when relevant:
  Overview
  Issues
  Suggestions
  Improved Code
`;

export function buildPrompt(task: AiTask, code: string, judgeEnabled: boolean): string {
  const taskInstruction = getTaskInstruction(task);
  const personality = judgeEnabled ? judgeMode : normalMode;

  return `
${personality}

${taskInstruction}

${baseRules}

Code:
\`\`\`
${code}
\`\`\`
`;
}

function getTaskInstruction(task: AiTask): string {
  if (task === "explain") {
    return `
Task:
Explain what this code does.

Required format:
Overview
Suggestions
`;
  }

  if (task === "fix") {
    return `
Task:
Find concrete problems and propose a fix.

Required format:
Overview
Issues
Suggestions
Improved Code
`;
  }

  return `
Task:
Review this code like a senior PR reviewer.
Only call out real issues visible in the code.
Avoid vague suggestions.

Required format:
Overview
Issues
Suggestions
Improved Code
`;
}
