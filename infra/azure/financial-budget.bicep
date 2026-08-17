targetScope = 'resourceGroup'

@description('Inicio do ciclo mensal do orçamento em formato ISO 8601.')
param budgetStartDate string

resource monthlyBudget 'Microsoft.Consumption/budgets@2023-05-01' = {
  name: 'usiedu-monthly-budget'
  properties: {
    amount: 30
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
    }
    notifications: {
      Actual_GreaterThanOrEqualTo_80_Percent: {
        contactEmails: []
        contactGroups: []
        contactRoles: []
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        thresholdType: 'Actual'
      }
      Actual_GreaterThanOrEqualTo_100_Percent: {
        contactEmails: []
        contactGroups: []
        contactRoles: []
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Actual'
      }
    }
  }
}

output budgetName string = monthlyBudget.name
