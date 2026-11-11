variable "control_plane_id" {
  description = "Konnect control plane ID"
  type        = string
}

variable "agent_url" {
  description = "Public URL of the A2A agent"
  type        = string
}

variable "agent_path" {
  description = "Route path for the agent on the gateway"
  type        = string
  default     = "/pet-agent-tf"
}

variable "proxy_url" {
  description = "Control plane proxy URL (for outputs)"
  type        = string
  default     = "https://<your-proxy-url>"
}

variable "require_api_key" {
  description = "Add key-auth to the route"
  type        = bool
  default     = false
}
