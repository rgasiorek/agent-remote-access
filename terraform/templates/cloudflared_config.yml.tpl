tunnel: ${tunnel_name}
credentials-file: ${credentials_file}

ingress:%{ if tunnel_hostname != "" ~}
  - hostname: ${tunnel_hostname}
    service: http://localhost:8000
  - service: http_status:404
%{ else ~}
  # No hostname specified - using free .cfargotunnel.com subdomain
  # Accessible at: https://${tunnel_id}.cfargotunnel.com
  - service: http://localhost:8000
%{ endif ~}
