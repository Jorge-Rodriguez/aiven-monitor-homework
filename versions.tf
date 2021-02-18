terraform {
  experiments = [module_variable_optional_attrs]

  required_version = ">= 0.14"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "2.11.0"
    }
    aiven = {
      source  = "aiven/aiven"
      version = "2.1.7"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.0.0"
    }
  }
}
