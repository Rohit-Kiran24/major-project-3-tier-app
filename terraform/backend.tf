terraform {
  # S3 remote backend — used in production deployments via GitHub Actions
  # For local development, run: terraform init -backend=false
  # For CI validation, the deploy.yml passes: terraform init -backend=false
  backend "s3" {
    bucket         = "rohit-3tier-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
