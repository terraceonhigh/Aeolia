# Aeolia — Claude Instructions

See README.md and docs/ for project overview.

## Inter-Agent Channel

A file-based message channel at `~/Labs/.claude-channel/` enables async communication between Cowork (Dispatch) and CLI sessions. Read `PROTOCOL.md` there for the full protocol.

**At session start, always run:**
```sh
cd ~/Labs/.claude-channel && ./channel.sh unread cli && ./channel.sh read cli
```

This surfaces any tasks or context updates Dispatch has queued since the last session.

The daemon (`daemon.sh`) runs continuously in the background, executing `type: task` messages automatically via the Claude Code CLI. Use `./ctl.sh start` to launch it, or load the launchd agent for auto-start on login:
```sh
cp ~/Labs/.claude-channel/launchd/com.claude.channel.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.claude.channel.plist
```
