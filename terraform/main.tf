terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.region
}

# 1. Zip local function source
data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../bankLoggingFunction"
  output_path = "${path.module}/bankLoggingFunction.zip"
}

# 2. Cloud Storage bucket to stage code
resource "google_storage_bucket" "source_bucket" {
  name                        = "${var.project_id}-gcf-source"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "source_zip" {
  name   = "source-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.function_zip.output_path
}

# 3. Dedicated Service Account
resource "google_service_account" "sync_sa" {
  account_id   = "revolut-sync-sa"
  display_name = "Revolut Sync Service Account"
}

# 4. Cloud Function (2nd Gen)
resource "google_cloudfunctions2_function" "revolut_function" {
  name        = "revolut-sync-function"
  location    = var.region
  description = "Syncs Revolut transactions to Google Sheets"

  build_config {
    runtime     = "python311"
    entry_point = "sync_revolut"
    source {
      storage_source {
        bucket = google_storage_bucket.source_bucket.name
        object = google_storage_bucket_object.source_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 1
    timeout_seconds       = 180
    service_account_email = google_service_account.sync_sa.email

    environment_variables = {
      EB_APP_ID      = var.eb_app_id
      EB_ACCOUNT_ID  = var.eb_account_id
      SPREADSHEET_ID = var.spreadsheet_id
      EB_PRIVATE_KEY = file("${path.module}/constants/ca8f898c-d201-4521-9814-3fcd63f791dd.pem")
    }
  }
}

# 5. Allow Service Account to invoke the Function
resource "google_cloud_run_service_iam_member" "invoker" {
  location = google_cloudfunctions2_function.revolut_function.location
  service  = google_cloudfunctions2_function.revolut_function.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.sync_sa.email}"
}

# 6. Cloud Scheduler (Runs every 6 hours)
resource "google_cloud_scheduler_job" "sync_schedule" {
  name             = "trigger-revolut-sync"
  schedule         = "0 */6 * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.revolut_function.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.sync_sa.email
    }
  }
}

output "service_account_email" {
  value       = google_service_account.sync_sa.email
  description = "Share your Google Sheet with this email address."
}