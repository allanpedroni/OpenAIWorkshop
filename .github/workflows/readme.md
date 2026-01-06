# Workflows

## infra-plan-apply.yml

### Summary

The infra plan and apply pipeline is a pipeline to deploy the infrastructure necessary for the Azure Open AI Workshop ot run. It is currently configured to do a workflow dispatch that expects you to choose whether you want bicep or terraform as well as a target environment. Terraform is currently tested. 

### Requirements

#### Environment Variables in GitHub

Configure your repo to have necessary variables for your environments. At a minimum, the following are needed:
- AZ_REGION: azure region you plan to deploy to
- AZURE_CLIENT_ID: the deployment client. Currently, this is used with an OIDC process so we don't need to set the secrets. Because of the way we are deploying, needs the ability to assign RBAC in Azure as well as creating resources.
- AZURE_SUBSCRIPTION_ID: the subscription to deploy into.
- AZURE_TENANT_ID: the tenant the client was created in
- DOCKER_IMAGE_BACKEND: docker image repo/name:tag from docker hub for backend FastAPI service. Still need to test with ACR. Also need to test with dynamic build from the repo.
- DOCKER_IMAGE_MCP: docker image repo/name:tag from docker hub for MCP service. Still need to test with ACR. Also need to test with dynamic build from the repo.

Required for terraform:
- TFSTATE_ACCOUNT: We expect an Azure Storage account for the backend. This is the account name.
- TFSTATE_CONTAINER: the blob container within the storage account where we will hold the state.
- TFSTATE_RG: resource group holding the storage account.

#### Azure Set Up

- Azure Subscription
- Resource group with a storage account for terraform
- Azure Service Principal (app registration) configured with federated credentials:

```
az ad app federated-credential create --id "$APP_ID" --parameters "$(jq -cn \
--arg org "$ORG" --arg repo "$REPO_NAME" '{
name: ("github-"+$repo+"-env-dev"),
issuer: "https://token.actions.githubusercontent.com",
subject: ("repo:"+$org+"/"+$repo+":environment:dev"),
audiences: ["api://AzureADTokenExchange"]
}')"
```