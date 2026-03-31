// ============================================================================
// Module: APIM Agent Behavioral Gateway
// Provides a runtime control layer in front of the AI Foundry Responses API.
//
// This module creates an APIM API that proxies calls to the Foundry project
// endpoint and applies the agent-gateway-policy.xml before forwarding them.
// Three runtime controls are available via request headers — no agent
// definition changes required:
//
//   X-Agent-Mode: read-only       — strip write_record + process_approval
//   X-Agent-Mode: no-delegation   — strip delegate_* tools
//   X-Context-Flags: <k=v,...>    — inject runtime flags as a system turn
//   X-Sub-Agent-Depth: <int>      — recursion guard (capped at MaxSubAgentDepth)
//
// Callers (the chat app, Teams bot, or any APIM consumer) target:
//   POST https://<apim>/agent-gateway/responses
// instead of the Foundry endpoint directly.  The policy rewrites the request
// and forwards it transparently.
// ============================================================================

@description('Name of the existing API Management instance')
param apimName string

@description('AI Foundry project Responses API base URL (e.g. https://<project>.services.ai.azure.com/api/projects/<proj>)')
param foundryProjectEndpoint string

// --------------------------------------------------------------------------
// Reference existing APIM instance
// --------------------------------------------------------------------------
resource apim 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

// --------------------------------------------------------------------------
// Backend — AI Foundry Responses API
// --------------------------------------------------------------------------
resource foundryBackend 'Microsoft.ApiManagement/service/backends@2024-06-01-preview' = {
  parent: apim
  name: 'foundry-responses-backend'
  properties: {
    url: foundryProjectEndpoint
    protocol: 'http'
    title: 'AI Foundry Responses API'
  }
}

// --------------------------------------------------------------------------
// Agent Gateway API
// --------------------------------------------------------------------------
resource agentGatewayApi 'Microsoft.ApiManagement/service/apis@2024-06-01-preview' = {
  parent: apim
  name: 'agent-gateway'
  properties: {
    displayName: 'Agent Behavioral Gateway'
    description: 'Runtime behavioral control layer for AI Foundry prompt agents. Supports read-only mode, delegation guards, and context flag injection via request headers — no agent definition changes required.'
    path: 'agent-gateway'
    protocols: [
      'https'
    ]
    subscriptionRequired: false
    apiType: 'http'
    serviceUrl: foundryProjectEndpoint
  }
}

// Responses endpoint — proxies to Foundry /openai/v1/responses
resource responsesOperation 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: agentGatewayApi
  name: 'responses'
  properties: {
    displayName: 'Create Agent Response'
    method: 'POST'
    urlTemplate: '/openai/v1/responses'
    description: 'Create a response from the Foundry prompt agent. Supports X-Agent-Mode and X-Context-Flags headers for runtime behavioral control.'
  }
}

// --------------------------------------------------------------------------
// API-level policy (behavioral rewriting)
// --------------------------------------------------------------------------
resource agentGatewayApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-06-01-preview' = {
  parent: agentGatewayApi
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('../policies/agent-gateway-policy.xml')
  }
  dependsOn: [
    foundryBackend
    maxSubAgentDepthNV
  ]
}

// --------------------------------------------------------------------------
// Reference the MaxSubAgentDepth Named Value (created by apim-sf-mcp-obo)
// --------------------------------------------------------------------------
resource maxSubAgentDepthNV 'Microsoft.ApiManagement/service/namedValues@2024-06-01-preview' existing = {
  parent: apim
  name: 'MaxSubAgentDepth'
}

// --------------------------------------------------------------------------
// Outputs
// --------------------------------------------------------------------------
@description('URL of the agent behavioral gateway')
output agentGatewayUrl string = '${apim.properties.gatewayUrl}/agent-gateway'

@description('Responses endpoint for agent calls via the gateway')
output responsesEndpoint string = '${apim.properties.gatewayUrl}/agent-gateway/openai/v1/responses'
