terraform {
  required_version = ">= 1.5.0"
}

variable "workload_name" {
  description = "A user-supplied name included in a future reviewed plan."
  type        = string
  default     = "ml-training-demo"
}

variable "cpu_cores" {
  type    = number
  default = 4
}

variable "memory_gb" {
  type    = number
  default = 16
}

output "review_summary" {
  value = {
    workload = var.workload_name
    cpu     = var.cpu_cores
    memory  = var.memory_gb
    notice  = "Template only. This module creates no cloud resources."
  }
}
