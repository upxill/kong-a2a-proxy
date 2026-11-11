output "agent_endpoint" {
  value = "${var.proxy_url}${var.agent_path}"
}

output "agent_card_url" {
  value = "${var.proxy_url}${var.agent_path}/.well-known/agent-card.json"
}
