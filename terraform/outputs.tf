output "tunnel_id" {
  description = "Cloudflare Tunnel ID"
  value       = cloudflare_zero_trust_tunnel_cloudflared.agent_remote_access.id
}

output "tunnel_cname" {
  description = "CNAME target for the tunnel"
  value       = "${cloudflare_zero_trust_tunnel_cloudflared.agent_remote_access.id}.cfargotunnel.com"
}

output "tunnel_url" {
  description = "Full HTTPS URL to access the tunnel"
  value       = var.tunnel_hostname != "" ? "https://${var.tunnel_hostname}" : "https://${cloudflare_zero_trust_tunnel_cloudflared.agent_remote_access.id}.cfargotunnel.com"
}

output "cloudflared_command" {
  description = "Command to run cloudflared locally"
  value       = "cloudflared tunnel run ${cloudflare_zero_trust_tunnel_cloudflared.agent_remote_access.name}"
}

output "credentials_file" {
  description = "Path to tunnel credentials file"
  value       = abspath("${path.module}/../.cloudflared/${cloudflare_zero_trust_tunnel_cloudflared.agent_remote_access.id}.json")
}
