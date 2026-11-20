terraform {
  required_version = ">= 1.9"

  # Plans and applies run in Terraform Cloud. A pull request gets a speculative plan; its JSON goes through the
  # plan guard (python -m epo.guard) before anyone can apply it. See docs/runbooks/infra_change.md.
  cloud {
    organization = "equity-platform"
    workspaces {
      tags = ["equity-platform"]
    }
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.14"
    }
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.26"
    }
  }
}

provider "google" {
  project = var.project_id
}

provider "mongodbatlas" {}
