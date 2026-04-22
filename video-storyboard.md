# Video Storyboard: Teams + AI Foundry + Salesforce MCP

**Duration target:** 60–90 seconds
**Format:** Animated diagram + screen recording combo
**Music:** Subtle tech/corporate background (royalty-free)

---

## Scene 1 — Hook (0:00–0:08)
**Type:** Text on screen (animated)
**Visual:** Bold text fades in on dark background:
> "What if your AI agent in Teams could query Salesforce — as YOU?"

**Voiceover/caption:** "Let me show you how identity flows from Teams to Salesforce in under 60 seconds."

---

## Scene 2 — The Ask (0:08–0:18)
**Type:** Screen recording
**Visual:** Open Microsoft Teams. Type a message in the chat:
> "Show me Contoso's open opportunities worth more than $50K"

**Voiceover/caption:** "A sales rep asks a question in Teams. Behind the scenes, a chain of secure token exchanges begins."

---

## Scene 3 — Architecture Animated Diagram (0:18–0:50)
**Type:** Animated diagram (use the Excalidraw diagram)
**Camera zooms through each layer progressively:**

### 3a — User Layer (0:18–0:23)
- Highlight: Sales Rep → Teams → Azure AD → Azure AD Token
- Caption: "The user signs in once via Azure AD SSO. A token is issued."

### 3b — AI Orchestration (0:23–0:30)
- Highlight: Teams → AI Foundry → AI Agent → MCP Tool Call
- Caption: "AI Foundry receives the message and the token. The agent decides it needs Salesforce data and invokes the MCP tool."

### 3c — Token Exchange in APIM (0:30–0:42)
- Highlight: APIM → Validate JWT → Resolve SF User → JWT Bearer OBO → SF Access Token
- Caption: "APIM validates the Azure AD token, maps the user's identity to their Salesforce username, and exchanges a JWT Bearer assertion for a per-user Salesforce access token. All cached for performance."

### 3d — Data Layer (0:42–0:50)
- Highlight: SF MCP Server → Salesforce Org → User's CRM Data → return arrow
- Caption: "The MCP server passes the token through — no credentials stored. Salesforce enforces the user's own permissions. Data flows back to Teams."

---

## Scene 4 — The Result (0:50–0:60)
**Type:** Screen recording
**Visual:** Back in Teams — the AI agent responds with a formatted table of Contoso's open opportunities, filtered to the user's access.

**Voiceover/caption:** "The rep gets their answer in seconds. Every step respected their identity. No shared service accounts. No credential leaks."

---

## Scene 5 — Key Takeaways (0:60–0:75)
**Type:** Text slides (animated)

Slide 1: "Per-user identity at every layer"
Slide 2: "Zero credentials in the AI layer"
Slide 3: "One sign-in — Azure AD SSO handles the rest"
Slide 4: "Works with Okta / PingFederate too"

---

## Scene 6 — CTA (0:75–0:90)
**Type:** Text on screen
**Visual:**
> "Building enterprise AI that respects identity isn't optional — it's table stakes."
> "Full article in the comments. Let's connect!"

---

## Recording Tips

1. **Screen recording:** Use OBS or Windows Game Bar. Record at 1080p.
2. **Teams demo:** Pre-load the conversation so the AI response appears quickly (or speed up the wait in editing).
3. **Diagram animation:** Export the Excalidraw diagram as frames or record it being drawn step-by-step.
4. **Editing:** Use CapCut (free) or DaVinci Resolve. Add captions as text overlays.
5. **LinkedIn specs:** Upload as MP4, 1080x1080 (square) or 1080x1350 (portrait) for max mobile visibility. Keep under 90 seconds for engagement.
