# Primus Production-To-Staging Data Mirror

This directory is packaged as the source asset for the `primus-prod-to-staging-data-mirror` CodeBuild project. The runner mirrors the Amplify `main` production DynamoDB/S3 data into `staging` inside the new AWS account.

Default mode is non-mutating preflight:

```bash
AWS_PROFILE=call-criteria AWS_REGION=us-east-1 aws codebuild start-build \
  --project-name primus-prod-to-staging-data-mirror \
  --environment-variables-override name=MIRROR_MODE,value=preflight,type=PLAINTEXT
```

Full destructive mirror requires explicit confirmation:

```bash
AWS_PROFILE=call-criteria AWS_REGION=us-east-1 aws codebuild start-build \
  --project-name primus-prod-to-staging-data-mirror \
  --environment-variables-override \
    name=MIRROR_MODE,value=full,type=PLAINTEXT \
    name=CONFIRM_DESTRUCTIVE,value=mirror-main-to-staging,type=PLAINTEXT
```

Cognito users are best-effort only. Cognito passwords and `sub` values cannot be copied. Set `STAGING_COGNITO_TEMP_PASSWORD` as a CodeBuild override only if staging users should be created with a temporary password.
