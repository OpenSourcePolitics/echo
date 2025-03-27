terraform {

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "~> 2.0"
    }
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.51.0"
    }
    # helm = {
    #   source  = "hashicorp/helm"
    #   version = "~> 2.0"
    # }
  }

  #  backend "s3" {
  #    endpoint                   = "https://ams3.digitaloceanspaces.com"
  #    bucket                     = "dbr-echo-tf-state-storage"
  #    key                        = "terraform.tfstate"
  #    region = "us-east-1" # Use any region (required but not actually used by Spaces)
  #    skip_credentials_validation = true        # Required for non-AWS S3 (DigitalOcean)
  #    skip_requesting_account_id = true
  #    skip_metadata_api_check    = true
  #    skip_region_validation     = true
  #    skip_s3_checksum           = true
  #  }
  # }

}



provider "scaleway" {
  region          = var.scw_region
  access_key      = var.scw_access_key
  secret_key      = var.scw_secret_key
  organization_id = var.scw_organization_id
  project_id      = var.scw_project_id
}

# provider "helm" {
#   kubernetes {
#     host                   = digitalocean_kubernetes_cluster.doks.kube_config.0.host
#     client_certificate     = digitalocean_kubernetes_cluster.doks.kube_config.0.client_certificate
#     client_key             = digitalocean_kubernetes_cluster.doks.kube_config.0.client_key
#     cluster_ca_certificate = digitalocean_kubernetes_cluster.doks.kube_config.0.cluster_ca_certificate
#   }
# }

# provider "kubernetes" {
#   host                   = digitalocean_kubernetes_cluster.doks.kube_config.0.host
#   client_certificate     = digitalocean_kubernetes_cluster.doks.kube_config.0.client_certificate
#   client_key             = digitalocean_kubernetes_cluster.doks.kube_config.0.client_key
#   cluster_ca_certificate = digitalocean_kubernetes_cluster.doks.kube_config.0.cluster_ca_certificate
# }
