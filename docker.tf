resource "docker_image" "monitor" {
  name = "aiven_monitor"

  build {
    path = path.module
  }
}

resource "docker_container" "url_monitor" {
  depends_on = [aiven_database.this] # Don't start the container until all aiven services are up

  image       = docker_image.monitor.latest
  name        = "url_monitor"
  entrypoint  = ["python3", "-m", "url_monitor", "monitor", "-c", "monitor.json"]
  restart     = "unless-stopped"
  working_dir = "/code"
  must_run    = true

  upload {
    source      = local_file.monitor.filename
    source_hash = base64sha256(local_file.monitor.sensitive_content)
    file        = "/code/monitor.json"
  }
  upload {
    content = data.aiven_project.this.ca_cert
    file    = "/code/ca.pem"
  }

  provisioner "local-exec" {
    command = "rm ${local_file.monitor.filename}"
  }
}

resource "docker_container" "writer" {
  image       = docker_image.monitor.latest
  name        = "writer"
  entrypoint  = ["python3", "-m", "url_monitor", "writer", "-c", "writer.json"]
  restart     = "unless-stopped"
  working_dir = "/code"
  must_run    = true

  upload {
    source      = local_file.writer.filename
    source_hash = base64sha256(local_file.writer.sensitive_content)
    file        = "/code/writer.json"
  }
  upload {
    content = data.aiven_project.this.ca_cert
    file    = "/code/ca.pem"
  }

  provisioner "local-exec" {
    command = "rm ${local_file.writer.filename}"
  }
}

resource "local_file" "monitor" {
  filename = "${path.module}/configs/monitor.json"
  sensitive_content = jsonencode({
    kafka = {
      connection = {
        "bootstrap.servers"   = "${aiven_kafka.broker.service_host}:${aiven_kafka.broker.service_port}"
        "security.protocol"   = "ssl"
        "ssl.key.pem"         = aiven_service_user.kafka["write"].access_key
        "ssl.certificate.pem" = aiven_service_user.kafka["write"].access_cert
        "ssl.ca.location"     = "/code/ca.pem"
      }
      topic = aiven_kafka_topic.this.topic_name
    }
    targets = [for target in var.integration ? local.integration_targets : var.targets : { for k, v in target : k => v if v != null }]
  })
}

resource "local_file" "writer" {
  filename = "${path.module}/configs/writer.json"
  sensitive_content = jsonencode({
    kafka = {
      connection = {
        "bootstrap.servers"   = "${aiven_kafka.broker.service_host}:${aiven_kafka.broker.service_port}"
        "group.id"            = "writer"
        "security.protocol"   = "ssl"
        "ssl.key.pem"         = aiven_service_user.kafka["read"].access_key
        "ssl.certificate.pem" = aiven_service_user.kafka["read"].access_cert
        "ssl.ca.location"     = "/code/ca.pem"
      }
      topics         = [aiven_kafka_topic.this.topic_name]
    }
    postgres = {
      connection = {
        host     = aiven_pg.db_server.service_host
        port     = aiven_pg.db_server.service_port
        user     = aiven_pg.db_server.service_username
        password = aiven_pg.db_server.service_password
        dbname   = aiven_database.this.database_name
      }
      batch_size = 10
    }
  })
}
