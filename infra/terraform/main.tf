locals {
  labels = {
    environment = var.environment
    managed_by  = "terraform"
    system      = "equity-platform"
  }
}

resource "google_compute_network" "main" {
  name                    = "equity-${var.environment}"
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
}

module "region" {
  source   = "./modules/region"
  for_each = var.regions

  name          = each.key
  environment   = var.environment
  project_id    = var.project_id
  region        = each.value.gcp_region
  network_id    = google_compute_network.main.id
  subnet_cidr   = each.value.subnet_cidr
  pods_cidr     = each.value.pods_cidr
  services_cidr = each.value.services_cidr
  master_cidr   = each.value.master_cidr
  labels        = local.labels
}

# One image registry for both regions: images are built once in CI and deployed by digest.
resource "google_artifact_registry_repository" "images" {
  location      = "europe"
  repository_id = "equity"
  format        = "DOCKER"
  labels        = local.labels

  docker_config {
    immutable_tags = true
  }

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 30
    }
  }
}

# The workloads' identity: Kubernetes service accounts in both clusters map to this one through Workload
# Identity, so no key files exist.
resource "google_service_account" "workloads" {
  account_id   = "equity-workloads"
  display_name = "equity API and workers"
}

resource "google_service_account_iam_member" "workload_identity" {
  for_each           = toset(["api", "worker"])
  service_account_id = google_service_account.workloads.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[equity/${each.key}]"
}

resource "google_project_iam_member" "workloads" {
  for_each = toset(["roles/secretmanager.secretAccessor", "roles/monitoring.metricWriter", "roles/logging.logWriter"])
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.workloads.email}"
}

resource "google_artifact_registry_repository_iam_member" "pull" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.workloads.email}"
}
