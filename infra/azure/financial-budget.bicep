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
  }
}

output budgetName string = monthlyBudget.name
