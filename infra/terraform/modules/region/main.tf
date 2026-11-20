resource "google_compute_subnetwork" "nodes" {
  name                     = "equity-${var.name}"
  region                   = var.region
  network                  = var.network_id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

# Private nodes reach the internet (Atlas, Temporal Cloud, Sentry) through NAT, with fixed egress addresses that
# go on the partners' allow lists.
resource "google_compute_router" "nat" {
  name    = "equity-${var.name}"
  region  = var.region
  network = var.network_id
}

resource "google_compute_address" "egress" {
  count  = 2
  name   = "equity-${var.name}-egress-${count.index}"
  region = var.region
}

resource "google_compute_router_nat" "nat" {
  name                               = "equity-${var.name}"
  router                             = google_compute_router.nat.name
  region                             = var.region
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = google_compute_address.egress[*].self_link
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

resource "google_container_cluster" "this" {
  name                = "equity-${var.name}"
  location            = var.region
  network             = var.network_id
  subnetwork          = google_compute_subnetwork.nodes.id
  deletion_protection = true
  resource_labels     = var.labels

  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = "REGULAR"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_cidr
  }

  datapath_provider = "ADVANCED_DATAPATH" # Dataplane V2: NetworkPolicy enforced without Calico

  maintenance_policy {
    recurring_window {
      start_time = "2026-01-03T01:00:00Z"
      end_time   = "2026-01-03T05:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA,SU"
    }
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
    managed_prometheus {
      enabled = true
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_container_node_pool" "general" {
  name     = "general"
  cluster  = google_container_cluster.this.id
  location = var.region

  autoscaling {
    min_node_count = var.min_nodes_per_zone
    max_node_count = var.max_nodes_per_zone
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    machine_type = var.node_machine_type
    disk_size_gb = 50
    disk_type    = "pd-balanced"
    labels       = var.labels
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot = true
    }
  }
}
