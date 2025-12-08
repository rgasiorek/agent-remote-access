tunnel: ${tunnel_name}
credentials-file: ${credentials_file}

ingress:
  - hostname: ${tunnel_hostname}
    service: http://localhost:8000
  - service: http_status:404
