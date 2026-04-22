# Teams as System of Engagement: Bringing Salesforce to Where Your Users Already Are

In my previous article, I showed how to build a Salesforce MCP server with real identity propagation — per-user access tokens flowing end-to-end, no shared service accounts.

Now: **where do users actually interact with this?**

---

Most of my customers already have Teams deployed. Everyone's in it — chat, meetings, daily workflows. It's the one app that's always open.

So instead of building another portal, I wanted to show something simple: **how we bring Salesforce data directly into Teams** with just an MCP server and Azure AI Foundry. No new UI. No change management. The interface is already adopted.

A user types "give me my open opportunities" in Teams. Behind the scenes, an **Azure AI Foundry** agent calls a Salesforce MCP tool through **Azure APIM**, and returns the user's own data — scoped to their permissions, their pipeline. No one else's.

&nbsp;

**The flow:** Teams → Azure AI Foundry → Azure APIM (OBO token exchange) → Salesforce MCP → back to Teams.

**AI Foundry** hosts the agent, manages the conversation, and acquires the user's Entra token automatically. **APIM** validates the JWT, resolves the SF username, and exchanges the token via JWT Bearer OBO — three phases, fully cached, zero credentials stored. The **MCP server** is stateless: receives a bearer token, calls Salesforce, returns the result. Swap Salesforce for SAP or ServiceNow — the pattern holds.

&nbsp;

The meta-tools pattern means any system with an API becomes queryable through the same channel. Teams becomes the **system of engagement** on top of all your **systems of record**.

The demo (video below) shows the full scenario live: SSO sign-in, natural language query in Teams, real-time token exchange, per-user Salesforce data returned — formatted, contextual, instant.

Enterprise AI that can't respect identity boundaries isn't enterprise-ready. The combination of **MCP**, **Azure AI Foundry**, **APIM**, and **Teams** makes it surprisingly achievable.

&nbsp;

Full architecture in my previous article. Code and IaC open — link in comments.

What systems would you connect first?

&nbsp;

#MicrosoftTeams #Salesforce #MCP #AzureAIFoundry #EnterpriseAI #IdentityPropagation #AIAgents #APIM
