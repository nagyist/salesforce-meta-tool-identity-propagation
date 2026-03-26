targetScope = 'subscription'

@description('Principal ID to assign the role to')
param principalId string

@description('Role definition ID (GUID only)')
param roleDefinitionId string

@description('Principal type')
param principalType string = 'ServicePrincipal'

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, principalId, roleDefinitionId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalType: principalType
  }
}
