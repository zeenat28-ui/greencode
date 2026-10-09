# Microsoft Azure Infrastructure for GreenCode
provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-greencode-${var.environment}"
  location = "eastus"
}

resource "azurerm_postgresql_flexible_server" "postgres" {
  name                   = "psql-greencode-${var.environment}"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "15"
  administrator_login    = "greencode_admin"
  administrator_password = "ReplaceWithAzureKeyVaultPassword2026!"
  sku_name               = "GP_Standard_D4ds_v5"
  storage_mb             = 131072
  backup_retention_days  = 30
}

resource "azurerm_redis_cache" "redis" {
  name                = "redis-greencode-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = 2
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
}

