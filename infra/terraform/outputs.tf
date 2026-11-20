output "clusters" {
  value = { for k, m in module.region : k => m.cluster_name }
}

output "registry" {
  value = "${google_artifact_registry_repository.images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "workload_service_account" {
  value = google_service_account.workloads.email
}

output "mongodb_srv" {
  value     = mongodbatlas_advanced_cluster.equity.connection_strings[0].standard_srv
  sensitive = true
}
