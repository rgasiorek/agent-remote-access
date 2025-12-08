output "tunnel_id" {
  description = "Cloudflare Tunnel ID"
  value       = cloudflare_tunnel.agent_remote_access.id
}

output "tunnel_cname" {
  description = "CNAME target for the tunnel"
  value       = "${cloudflare_tunnel.agent_remote_access.id}.cfargotunnel.com"
}

output "tunnel_url" {
  description = "Full HTTPS URL to access the tunnel"
  value       = "https://${var.tunnel_hostname}"
}

output "cloudflared_command" {
  description = "Command to run cloudflared locally"
  value       = "cloudflared tunnel run ${cloudflare_tunnel.agent_remote_access.name}"
}

output "credentials_file" {
  description = "Path to tunnel credentials file"
  value       = abspath("${path.module}/../.cloudflared/${cloudflare_tunnel.agent_remote_access.id}.json")
}
