---
name: GitHub source control access
description: What to do when GitHub integration state and git push authentication disagree.
---

When a GitHub source-control connection appears authorized but `git push` is rejected, verify the actual remote state rather than assuming the repository is already synced. Replit's documented recovery is to disconnect and reconnect GitHub under account Settings → Connected Services.

**Why:** The account integration can report an active connection while Git CLI authentication still fails; repeating local push or integration-binding attempts does not repair the account authorization.

**How to apply:** Confirm the target remote and whether it has branches, retain local commits, and ask the user to refresh GitHub under Connected Services. Never request a GitHub password or token in chat.
