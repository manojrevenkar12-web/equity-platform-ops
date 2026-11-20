data "google_project" "this" {
  project_id = var.project_id
}

# Spend alerts at 50, 80 and 100 % of the month, and on the forecast passing 100 %: a cost change is a review
# conversation before it is an invoice.
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "equity-${var.environment}"

  budget_filter {
    projects               = ["projects/${data.google_project.this.number}"]
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.monthly_budget_eur)
    }
  }

  dynamic "threshold_rules" {
    for_each = [0.5, 0.8, 1.0]
    content {
      threshold_percent = threshold_rules.value
    }
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = var.budget_alert_channels
    disable_default_iam_recipients   = length(var.budget_alert_channels) > 0
  }
}
