locals {
  integration_targets = [
    {
      url       = "https://ipecho.net/plain"
      frequency = 30
      regex     = "(?:\\d{1,3}\\.){3}\\d{1,3}"
    },
    {
      url       = "https://www.google.com/"
      frequency = 15
    }
  ]
}

resource "local_file" "config" {
  count = var.integration ? 1 : 0

  filename = "${path.module}/integration/config.json"
  sensitive_content = jsonencode({
    targets      = local.integration_targets
    initial_wait = max([for target in local.integration_targets : target.frequency]...) + 5
    postgres = {
      host     = aiven_pg.db_server.service_host
      port     = aiven_pg.db_server.service_port
      user     = aiven_pg.db_server.service_username
      password = aiven_pg.db_server.service_password
      dbname   = aiven_database.this.database_name
    }
  })
}

resource "docker_image" "integration" {
  count = var.integration ? 1 : 0

  name = "aiven_monitor_integration_tests"
  build {
    path = "${path.module}/integration"
  }
}

resource "docker_container" "integration" {
  count      = var.integration ? 1 : 0
  depends_on = [docker_container.url_monitor, docker_container.writer]

  image       = docker_image.integration[0].latest
  name        = "integration_tests"
  entrypoint  = ["pytest"]
  working_dir = "/code"
  restart     = "no"
  must_run    = false
  attach      = true
  logs        = true

  upload {
    source      = local_file.config[0].filename
    source_hash = base64sha256(local_file.config[0].sensitive_content)
    file        = "/code/tests/config.json"
  }

  provisioner "local-exec" {
    command = "rm ${local_file.config[0].filename}"
  }
}

output "integration_logs" {
  value = try(docker_container.integration[0].container_logs, null)
}
