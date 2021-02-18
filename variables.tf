variable "integration" {
  description = "Tag indicating whether terraform should apply integration testing resources"
  type        = bool
  default     = false
}

variable "targets" {
  description = "List of URLs to monitor"
  type = list(object({
    url       = string
    frequency = number
    regex     = optional(string)
  }))
}
