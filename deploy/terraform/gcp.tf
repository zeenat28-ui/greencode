# Google Cloud Platform Infrastructure for GreenCode
provider "google" {
  project = "greencode-enterprise"
  region  = "us-central1"
}

resource "google_sql_database_instance" "postgres" {
  name             = "greencode-${var.environment}-pg"
  database_version = "POSTGRES_15"
  region           = "us-central1"

  settings {
    tier              = "db-custom-4-16384"
    availability_type = "REGIONAL"
    disk_size         = 100
    disk_type         = "PD_SSD"
    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }
  }
}

