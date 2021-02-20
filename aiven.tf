locals {
  cloud_name = "google-europe-north1"
}

data "aiven_project" "this" {
  project = "jorge-9430"
}

resource "aiven_kafka" "broker" {
  project    = data.aiven_project.this.project
  cloud_name = local.cloud_name
  plan       = "startup-2"

  service_name = "urlmonitorbroker${var.integration ? "integration" : ""}"

  termination_protection = false # we're not selling this just yet
}

resource "aiven_kafka_topic" "this" {
  project      = data.aiven_project.this.project
  service_name = aiven_kafka.broker.service_name
  topic_name   = "url_monitor"

  partitions  = 3
  replication = 2

  termination_protection = false
}

resource "aiven_service_user" "kafka" {
  for_each = toset(["read", "write"])

  project      = data.aiven_project.this.project
  service_name = aiven_kafka.broker.service_name
  username     = "kafka_${each.value}"
}

resource "aiven_kafka_acl" "this" {
  for_each = aiven_service_user.kafka

  project      = data.aiven_project.this.project
  service_name = aiven_kafka.broker.service_name
  topic        = aiven_kafka_topic.this.topic_name
  permission   = each.key
  username     = each.value.username
}

resource "aiven_pg" "db_server" {
  project      = data.aiven_project.this.project
  cloud_name   = local.cloud_name
  plan         = "hobbyist"
  service_name = "urlmonitordatabase${var.integration ? "integration" : ""}"

  termination_protection = false
}

resource "aiven_database" "this" {
  project       = data.aiven_project.this.project
  service_name  = aiven_pg.db_server.service_name
  database_name = "url_monitor"
}
