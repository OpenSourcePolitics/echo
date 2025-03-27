// spaces output
// ams3.digitaloceanspaces.com
// bucket name (dev)  : dbr-echo-dev-uploads.ams3.digitaloceanspaces.com
// bucket name (prod) : dbr-echo-prod-uploads.ams3.digitaloceanspaces.com

// rdb output
output "rdb_name" {
  value = var.rdb_name
}
output "rdb_ip" {
    value = scaleway_rdb_instance.main.load_balancer[0].ip
}