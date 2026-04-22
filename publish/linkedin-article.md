# Your AI Agent in Teams Just Got Access to Salesforce — With Zero Shared Passwords

Last month I shared how I built a Salesforce MCP server. Today, I want to show you what happens when you plug it into **Microsoft Teams** with full identity propagation.

Here's the scenario: a sales rep asks a question in Teams. An AI agent powered by **Azure AI Foundry** understands the intent, calls a Salesforce tool, and returns CRM data — all under **that user's own Salesforce identity**. No shared service accounts. No credential leaks. No shortcuts.

---

## How It Works (60-Second Version)

**The user sends a message in Teams.** The Bot Service routes it to a FastAPI backend, which forwards it to Azure AI Foundry's Responses API along with the user's Azure AD token.

**AI Foundry picks the right tool.** The agent decides it needs Salesforce data and invokes the MCP tool. Foundry exchanges the user's token for one scoped to the APIM gateway — preserving the user's identity.

**APIM does the heavy lifting.** This is where the magic happens. A three-phase policy:

1. **Validates** the Azure AD token and extracts the user's object ID
2. **Resolves** the Salesforce username by querying SF with: *"Which SF user has this Azure AD identity?"*
3. **Exchanges** a JWT Bearer assertion (signed with a Key Vault certificate) for a per-user Salesforce access token

All three phases are cached — warm requests add near-zero latency.

**The MCP server gets a clean Salesforce token.** It simply passes it through to the Salesforce REST API. No credentials stored. Salesforce enforces that user's sharing rules, field-level security, and approval workflows.

**Data flows back** through the same chain — MCP → APIM → Foundry → Teams — and the rep gets their answer in the chat.

---

## Why This Matters

Most enterprise AI integrations use a single service account — meaning the AI sees everything, regardless of who's asking. This design enforces **per-user permissions at every layer**. If a rep can't see an account in Salesforce, the AI can't either.

It also means:

- **Zero credentials in the AI layer** — the MCP server never stores tokens
- **One sign-in** — Azure AD SSO handles the rest
- **Swappable IdP** — the APIM policy works with Okta or PingFederate too, not just Azure AD

---

## See It in Action

Watch the video below to see the full flow — from a Teams message to Salesforce data appearing in the chat, with a step-by-step animation of the token exchange.

---

*Building enterprise AI that respects identity isn't optional — it's table stakes. If you're connecting LLMs to business data, make sure the "who" travels with the "what."*

#AI #Salesforce #MicrosoftTeams #AzureAIFoundry #MCP #EnterpriseAI #Identity #OAuth #Security
