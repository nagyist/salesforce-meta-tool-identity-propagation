# In the Agent Era, SaaS Systems Risk Becoming Just Systems of Record

In Part 1, I built an MCP server that lets an AI agent query Salesforce with the end user's own identity — real per-user tokens flowing through Azure APIM via JWT Bearer OBO.

That was the technical foundation. But while building it, a broader idea started forming in my mind.

&nbsp;

---

&nbsp;

## An Idea Worth Exploring

Today we have dozens of SaaS systems — Salesforce, ServiceNow, SAP, Workday — each with its own UI, its own login, its own learning curve. Every system is a destination.

But what if, with AI agents, that changes? What if the **meta-tools pattern** — where any SaaS API becomes a tool an agent can call on your behalf — gradually turns these platforms into something different? They'd still hold the data, still enforce security. But users might no longer need to go there directly. SaaS could shift from **destination** to **system of record**, with agents bringing the data to wherever you already are.

I'm not saying this will definitely happen. But it's a possibility I find worth thinking about.

&nbsp;

## What I Built to Test This Idea

To explore this, I connected my MCP tool to **Azure AI Foundry** as the orchestration layer, then brought that agent into **Microsoft Teams** — because most of my customers already use it. It's deployed, adopted, always open.

**Teams → AI Foundry → APIM (OBO token exchange) → Salesforce MCP → back to Teams.**

A user types "show me my open opportunities." The agent calls the MCP tool, APIM exchanges the token respecting the user's identity, Salesforce returns only that user's data. Right there in Teams — no tab switch, no separate login.

It felt surprisingly natural. And that's what got me thinking.

&nbsp;

## Why the Pattern Is Interesting

What struck me isn't the Salesforce integration itself — it's that the pattern is repeatable. An MCP server is stateless: bearer token in, API call, result out. You could swap Salesforce for SAP or ServiceNow and the architecture would stay the same.

Imagine one MCP tool per system, all connected to the same agent. Users would get a single conversational interface to every system of record — with their own permissions enforced end-to-end. The AI layer would never touch a password.

That's a lot of possibility from a fairly simple pattern.

&nbsp;

## A Thought to Share

Maybe our SaaS investments wouldn't become obsolete in this model — maybe they'd become more valuable. Every system, every dataset, every permission model we've built could become accessible through a single conversational layer.

MCP for tool abstraction. AI Foundry for orchestration. APIM for identity propagation. And Teams — already on every desktop — as a natural **system of engagement** sitting on top of all our **systems of record**.

I don't know if this is where enterprise software is headed. But after building it, I think it's a possibility worth considering.

&nbsp;

---

&nbsp;

Architecture details and code in Part 1. Repository link in comments.

What do you think — does this resonate with what you're seeing? I'd love to hear other perspectives.

&nbsp;

#MetaTools #MCP #EnterpriseAI #AzureAIFoundry #MicrosoftTeams #Salesforce #IdentityPropagation #AIAgents #APIM #SystemOfRecord
