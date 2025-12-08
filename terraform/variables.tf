variable "cloudflare_api_token" {
  description = "Cloudflare API token with Tunnel permissions"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for your domain"
  type        = string
}

variable "tunnel_hostname" {
  description = "Full hostname for the tunnel (e.g., remote-agent.yourdomain.com)"
  type        = string
}

variable "tunnel_subdomain" {
  description = "Subdomain for the tunnel (e.g., remote-agent)"
  type        = string
}
