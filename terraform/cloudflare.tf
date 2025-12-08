terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Generate random secret for tunnel
resource "random_password" "tunnel_secret" {
  length  = 64
  special = false
}

# Create Cloudflare Tunnel
resource "cloudflare_tunnel" "agent_remote_access" {
  account_id = var.cloudflare_account_id
  name       = "agent-remote-access"
  secret     = base64encode(random_password.tunnel_secret.result)
}

# Configure tunnel ingress rules
resource "cloudflare_tunnel_config" "agent_remote_access" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_tunnel.agent_remote_access.id

  config {
    # Only add hostname rule if custom domain is configured
    dynamic "ingress_rule" {
      for_each = var.tunnel_hostname != "" ? [1] : []
      content {
        hostname = var.tunnel_hostname
        service  = "http://localhost:8000"
      }
    }

    # Catch-all rule (required) - routes all traffic if no custom domain
    ingress_rule {
      service = "http://localhost:8000"
    }
  }
}

# Create DNS record pointing to the tunnel (only if zone_id is provided)
resource "cloudflare_record" "agent_remote_access" {
  count   = var.cloudflare_zone_id != "" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.tunnel_subdomain
  value   = "${cloudflare_tunnel.agent_remote_access.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true
  comment = "Claude Code Remote Access Tunnel"
}

# Output tunnel credentials for local cloudflared config
resource "local_file" "tunnel_credentials" {
  content = jsonencode({
    AccountTag   = var.cloudflare_account_id
    TunnelSecret = random_password.tunnel_secret.result
    TunnelID     = cloudflare_tunnel.agent_remote_access.id
    TunnelName   = cloudflare_tunnel.agent_remote_access.name
  })
  filename        = "${path.module}/../.cloudflared/${cloudflare_tunnel.agent_remote_access.id}.json"
  file_permission = "0600"
}

# Output cloudflared config file
resource "local_file" "cloudflared_config" {
  content = templatefile("${path.module}/templates/cloudflared_config.yml.tpl", {
    tunnel_id          = cloudflare_tunnel.agent_remote_access.id
    tunnel_name        = cloudflare_tunnel.agent_remote_access.name
    credentials_file   = abspath("${path.module}/../.cloudflared/${cloudflare_tunnel.agent_remote_access.id}.json")
    tunnel_hostname    = var.tunnel_hostname
  })
  filename        = "${path.module}/../.cloudflared/config.yml"
  file_permission = "0644"
}
