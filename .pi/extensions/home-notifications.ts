import { spawn } from "node:child_process";
import { basename } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

function run(command: string, args: string[]): void {
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.unref();
}

function notify(title: string, body: string, cwd: string): void {
  const subtitle = basename(cwd);
  if (process.env.CMUX_SURFACE_ID) {
    run("cmux", ["notify", "--title", title, "--subtitle", subtitle, "--body", body, "--surface", process.env.CMUX_SURFACE_ID]);
    return;
  }
  const script = `display notification ${JSON.stringify(body)} with title ${JSON.stringify(title)} subtitle ${JSON.stringify(subtitle)}`;
  run("osascript", ["-e", script]);
}

export default function homeNotifications(pi: ExtensionAPI): void {
  pi.on("agent_settled", async (_event, ctx) => notify("Pi finished", "Ready for your next instruction.", ctx.cwd));
  pi.on("ui_prompt_start", async (event, ctx) => {
    notify("Pi needs attention", event.title ? `Waiting: ${event.title}` : "Waiting for your input.", ctx.cwd);
  });
}
