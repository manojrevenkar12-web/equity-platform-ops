output "cluster_name" {
  value = google_container_cluster.this.name
}

output "egress_ips" {
  value = google_compute_address.egress[*].address
}
