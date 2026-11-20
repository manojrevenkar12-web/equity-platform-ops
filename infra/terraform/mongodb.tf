# The cap table and vesting events live in one Atlas cluster across three regions: two electable nodes in each
# main region and one tiebreaker, so losing a whole region keeps a majority and the primary moves (about 10 s
# of failed writes, which the activities retry). Reads stay on the primary: a vesting run must see its own writes.
resource "mongodbatlas_advanced_cluster" "equity" {
  project_id                     = var.atlas_project_id
  name                           = "equity-${var.environment}"
  cluster_type                   = "REPLICASET"
  mongo_db_major_version         = "7.0"
  backup_enabled                 = true
  pit_enabled                    = true
  termination_protection_enabled = true

  replication_specs {
    dynamic "region_configs" {
      for_each = var.regions
      content {
        provider_name = "GCP"
        region_name   = region_configs.value.atlas_region
        priority      = region_configs.value.primary ? 7 : 6
        electable_specs {
          instance_size = "M30"
          node_count    = 2
        }
        auto_scaling {
          disk_gb_enabled            = true
          compute_enabled            = true
          compute_max_instance_size  = "M50"
          compute_min_instance_size  = "M30"
          compute_scale_down_enabled = true
        }
      }
    }
    region_configs {
      provider_name = "GCP"
      region_name   = var.atlas_tiebreaker_region
      priority      = 5
      electable_specs {
        instance_size = "M30"
        node_count    = 1
      }
    }
  }

  advanced_configuration {
    javascript_enabled           = false
    minimum_enabled_tls_protocol = "TLS1_2"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Only the clusters' fixed NAT addresses may connect: no 0.0.0.0/0 on the access list, ever (the plan guard
# blocks it as well).
locals {
  egress = { for pair in flatten([for k in keys(var.regions) : [for i in range(2) : { key = "${k}-${i}", region = k, i = i }]]) : pair.key => pair }
}

resource "mongodbatlas_project_ip_access_list" "egress" {
  for_each   = local.egress
  project_id = var.atlas_project_id
  ip_address = module.region[each.value.region].egress_ips[each.value.i]
  comment    = "GKE egress ${each.key}"
}
