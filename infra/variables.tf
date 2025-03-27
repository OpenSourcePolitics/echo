variable "env" {
  type        = string
  description = "Environment name (dev or prod)"
}

variable "rdb_name" {
  type        = string
  description = "RDB database name"
  default = "dembrane"
}

variable "rdb_user" {
  type        = string
  description = "RDB user name"
  default = "dembrane"
}

variable "rdb_password" {
  type        = string
  description = "RDB user password"
  sensitive = true
}

variable "redis_user_name" {
  type        = string
  description = "Redis user name"
}

variable "redis_user_password" {
  type        = string
  description = "Redis user password"
  sensitive = true
}

variable "scw_region" {
  type        = string
  description = "SCW Region"
}

variable "scw_access_key" {
  type        = string
  description = "SCW Access key"
  sensitive = true
}

variable "scw_secret_key" {
  type        = string
  description = "SCW Secret key"
  sensitive = true
}

variable "scw_organization_id" {
  type        = string
  description = "SCW Organization ID"
  sensitive = true
}

variable "scw_project_id" {
  type        = string
  description = "SCW Project ID"
  sensitive = true
}
