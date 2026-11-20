variable "name" { type = string }
variable "environment" { type = string }
variable "project_id" { type = string }
variable "region" { type = string }
variable "network_id" { type = string }
variable "subnet_cidr" { type = string }
variable "pods_cidr" { type = string }
variable "services_cidr" { type = string }
variable "master_cidr" { type = string }
variable "labels" { type = map(string) }

variable "node_machine_type" {
  type    = string
  default = "e2-standard-4"
}

variable "min_nodes_per_zone" {
  type    = number
  default = 1
}

variable "max_nodes_per_zone" {
  type    = number
  default = 4
}
