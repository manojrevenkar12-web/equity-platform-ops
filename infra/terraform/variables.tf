variable "project_id" {
  type        = string
  description = "GCP project for the environment"
}

variable "environment" {
  type    = string
  default = "production"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment is staging or production"
  }
}

variable "regions" {
  description = "The two regions. The primary serves the API; workers poll in both, so a lost region costs minutes, not a run."
  type = map(object({
    gcp_region    = string
    atlas_region  = string
    primary       = bool
    subnet_cidr   = string
    pods_cidr     = string
    services_cidr = string
    master_cidr   = string
  }))
  default = {
    zurich = {
      gcp_region    = "europe-west6"
      atlas_region  = "EUROPE_WEST_6"
      primary       = true
      subnet_cidr   = "10.10.0.0/20"
      pods_cidr     = "10.110.0.0/16"
      services_cidr = "10.210.0.0/20"
      master_cidr   = "172.16.0.0/28"
    }
    frankfurt = {
      gcp_region    = "europe-west3"
      atlas_region  = "EUROPE_WEST_3"
      primary       = false
      subnet_cidr   = "10.20.0.0/20"
      pods_cidr     = "10.120.0.0/16"
      services_cidr = "10.220.0.0/20"
      master_cidr   = "172.16.0.16/28"
    }
  }
  validation {
    condition     = length([for r in values(var.regions) : r if r.primary]) == 1
    error_message = "exactly one region is primary"
  }
}

variable "atlas_project_id" {
  type        = string
  description = "MongoDB Atlas project"
}

variable "atlas_tiebreaker_region" {
  type        = string
  default     = "WESTERN_EUROPE"
  description = "A third Atlas region with one electable node, so either main region can be lost and a majority remains"
}

variable "billing_account" {
  type = string
}

variable "monthly_budget_eur" {
  type    = number
  default = 9000
}

variable "budget_alert_channels" {
  type        = list(string)
  default     = []
  description = "Monitoring notification channels (PagerDuty low-urgency, e-mail) for budget thresholds"
}
