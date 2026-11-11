terraform {
  required_providers {
    konnect = { source = "kong/konnect" }
  }
}

provider "konnect" {
  server_url = "https://us.api.konghq.com" # token from env KONNECT_TOKEN
}

resource "konnect_gateway_service" "pet_agent" {
  control_plane_id = var.control_plane_id
  name             = "pet-agent-tf"
  url              = var.agent_url
  read_timeout     = 120000
  tags             = ["a2a-terraform"]
}

resource "konnect_gateway_route" "pet_agent" {
  control_plane_id = var.control_plane_id
  name             = "pet-agent-tf"
  paths            = [var.agent_path]
  strip_path       = true
  service          = { id = konnect_gateway_service.pet_agent.id }
  tags             = ["a2a-terraform"]
}

resource "konnect_gateway_plugin_ai_a2a_proxy" "pet_agent" {
  control_plane_id = var.control_plane_id
  enabled          = true
  route            = { id = konnect_gateway_route.pet_agent.id }
  tags             = ["a2a-terraform"]

  config = {
    logging = {
      log_statistics   = true
      log_payloads     = false
      max_payload_size = 1048576
    }
    max_request_body_size = 1048576
  }
}

resource "konnect_gateway_plugin_key_auth" "pet_agent" {
  count            = var.require_api_key ? 1 : 0
  control_plane_id = var.control_plane_id
  route            = { id = konnect_gateway_route.pet_agent.id }
  config           = { key_names = ["apikey"], hide_credentials = true }
  tags             = ["a2a-terraform"]
}
