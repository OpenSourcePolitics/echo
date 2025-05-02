resource "scaleway_vpc_private_network" "pn" {
  name = "dbr-echo-${var.env}-pn"
  tags = ["dbr-echo", var.env, "k8s", "owner:quentin"]
}

resource "scaleway_k8s_cluster" "cluster" {
  name                        = "dbr-echo-${var.env}-cluster"
  type                        = "kapsule"
  description                 = "Main kubernetes cluster"
  version                     = "1.31.7"
  cni                         = "cilium"
  private_network_id          = scaleway_vpc_private_network.pn.id
  delete_additional_resources = false
  tags                        = ["dbr-echo", var.env, "k8s", "owner:quentin"]
}

resource "scaleway_k8s_pool" "pool" {
  cluster_id = scaleway_k8s_cluster.cluster.id
  name       = "dbr-echo-${var.env}-rdb-pool"
  node_type  = "DEV1-L"
  size       = 1
  max_size   = 2
  tags       = ["dbr-echo", var.env, "k8s", "owner:quentin"]
}

resource "scaleway_rdb_instance" "main" {
  name              = "dbr-echo-${var.env}-rdb"
  node_type         = var.env == "prod" ? "DB-PLAY2-NANO" : "DB-PLAY2-PICO"
  engine            = "PostgreSQL-16"
  is_ha_cluster     = true
  disable_backup    = true
  user_name         = var.rdb_user
  password          = var.rdb_password
  volume_type       = "bssd"
  volume_size_in_gb = 20
  tags              = ["dbr-echo", var.env, "k8s", "owner:quentin"]
}

resource "scaleway_rdb_database" "main" {
  instance_id = scaleway_rdb_instance.main.id
  name        = "dbrecho"
}

resource "scaleway_redis_cluster" "main" {
  name         = "dbr-echo-${var.env}-redis"
  version      = "6.2.7"
  node_type    = "RED1-MICRO"
  user_name    = var.redis_user_name
  password     = var.redis_user_password
  cluster_size = 1
  tls_enabled  = "true"
  tags         = ["dbr-echo", var.env, "k8s", "owner:quentin"]

  acl {
    ip          = "0.0.0.0/0"
    description = "Allow all"
  }
  settings = {
    "maxclients"    = "1000"
    "tcp-keepalive" = "120"
  }
}