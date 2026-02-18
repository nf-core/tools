# Setting up Slack notifications for nf-core pipelines

nf-core pipelines use the [nf-slack plugin](https://github.com/seqeralabs/nf-slack) (v0.4.1+) to send Slack notifications when cloud tests run via CI/CD. Notifications are sent using a Slack bot token, which posts messages on pipeline completion and failure.

Slack notifications are **disabled by default** for local runs. They only activate when a cloud test is triggered via GitHub Actions (PR approval, release, or manual dispatch).

## Prerequisites

- The pipeline is based on the nf-core template (which includes the cloud test workflow)
- You have admin access to the pipeline's GitHub repository
- You have access to the nf-core Slack workspace to create channels and invite the bot

## Setup

### 1. Create a Slack channel

Create a channel for your pipeline's CI notifications, e.g. `#{{ short_name }}`. If you already have a suitable channel, you can use that instead.

### 2. Invite the bot to the channel

> **Note for the nf-core core team:** The bot cannot be added to channels automatically. When onboarding a new pipeline, this step must be done manually. Consider adding this to the new pipeline checklist.

The nf-core Slack bot must be a member of any channel it posts to. The bot **will silently fail** to send messages if it is not a member of the target channel.

To invite it, type `/invite @nf-core-bot` (or the bot's actual name) in the channel. You can verify the bot is present by opening the channel details and checking the **Integrations** tab.

### 3. Ensure the bot token secret is available

The `NFSLACK_BOT_TOKEN` secret must be accessible to your pipeline's GitHub Actions. This is configured as an org-wide secret on the `nf-core` GitHub organization, so no per-repo setup should be needed.

If you are running this outside the nf-core organization, you need to add `NFSLACK_BOT_TOKEN` as a repository or organization secret containing your Slack bot's `xoxb-` token. See the [nf-slack bot setup docs](https://seqeralabs.github.io/nf-slack/latest/getting-started/bot-setup/) for how to create a Slack app and obtain a bot token.

### 4. Set the channel and messages in the cloud test workflow

In your pipeline's `.github/workflows/awsfulltest.yml`, find the `nextflow_config` block in the `seqeralabs/action-tower-launch` step and update the channel name and pipeline name. The nf-slack plugin is declared and configured entirely within the CI workflow — no changes to the pipeline's `nextflow.config` are needed.

```yaml
nextflow_config: |
  plugins {
    id 'nf-slack@0.4.1'
  }
  slack {
    enabled = true
    bot {
      token = '${{ "{{" }} secrets.NFSLACK_BOT_TOKEN {{ "}}" }}'
      channel = '{{ short_name }}'
    }
    onStart {
      enabled = false
    }
    onComplete {
      message = ':white_check_mark: *{{ short_name }}/${{ "{{" }} matrix.profile {{ "}}" }}* completed successfully! :tada:'
    }
    onError {
      message = ':x: *{{ short_name }}/${{ "{{" }} matrix.profile {{ "}}" }}* failed :crying_cat_face:'
    }
  }
```

The config is kept minimal by relying on plugin defaults. The following are all enabled by default and don't need to be set explicitly: `validateOnStartup`, `seqeraPlatform.enabled`, `showFooter`, `includeCommandLine`, `includeResourceUsage`, `onComplete.enabled`, `onError.enabled`.

Replace the channel with your channel name (without the `#` prefix), e.g. `mytools_dev`.

The token is injected directly from the GitHub secret. GitHub Actions automatically masks secret values in logs.

### Notification behavior

- **Start**: disabled — no notification when the pipeline begins
- **Success**: posts a message with the pipeline name, profile, success emoji, command line, resource usage, timestamp footer, and a "View in Seqera Platform" button (when run via Platform)
- **Failure**: posts a message with the pipeline name, profile, failure emoji, command line, resource usage, timestamp footer, and a "View in Seqera Platform" button (when run via Platform)
- **Token validation**: on startup, the plugin validates the bot token and logs a warning if invalid (default behavior)
- **Seqera Platform**: auto-detected when running via Platform, adds a button linking to the run (default behavior)

### Configuration options reference

| Option                 | Scope                  | Default | Description                                             |
| ---------------------- | ---------------------- | ------- | ------------------------------------------------------- |
| `enabled`              | `slack`                | `false` | Master switch for all notifications                     |
| `validateOnStartup`    | `slack`                | `true`  | Validate bot token on pipeline startup                  |
| `enabled`              | `bot`                  | -       | Use bot token auth (recommended over webhook)           |
| `token`                | `bot`                  | -       | Slack bot `xoxb-` token                                 |
| `channel`              | `bot`                  | -       | Target channel (no `#` prefix)                          |
| `enabled`              | `seqeraPlatform`       | `true`  | Enable Seqera Platform integration                      |
| `enabled`              | `onStart`              | `true`  | Send notification on pipeline start                     |
| `enabled`              | `onComplete`           | `true`  | Send notification on successful completion              |
| `enabled`              | `onError`              | `true`  | Send notification on pipeline failure                   |
| `message`              | `onComplete`/`onError` | -       | Custom message text (supports Slack markdown and emoji) |
| `showFooter`           | `onComplete`/`onError` | `true`  | Show completion timestamp and duration                  |
| `includeCommandLine`   | `onComplete`/`onError` | `true`  | Include the Nextflow command that was run               |
| `includeResourceUsage` | `onComplete`/`onError` | `true`  | Include task statistics and resource usage              |
| `files`                | `onComplete`/`onError` | `[]`    | File paths to upload with the notification (bot only)   |
| `useThreads`           | `slack`                | `false` | Group notifications in threads                          |

See the [nf-slack configuration docs](https://seqeralabs.github.io/nf-slack/latest/usage/configuration/) for all options.

## How it works

The nf-slack plugin is **not declared in the pipeline's `nextflow.config`** at all. It is entirely injected via the CI workflow's `nextflow_config` parameter, so local runs are completely unaffected.

When cloud tests run via GitHub Actions, the workflow:

1. Injects a `nextflow_config` block that declares the nf-slack plugin and its full configuration (bot token, channel, messages)
2. Nextflow merges this with the pipeline's own config, adding the plugin at runtime
3. The nf-slack plugin validates the token on startup, then posts notifications to the specified Slack channel on completion or failure

**Important:** The `envvars` parameter of `seqeralabs/action-tower-launch` does not exist. Environment variables cannot be passed this way. The token must be injected directly into the `nextflow_config` block.

## Troubleshooting

| Problem                                   | Solution                                                                                      |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| No messages appear in the channel         | Verify the bot has been invited to the channel                                                |
| Authentication errors in the pipeline log | Check that `NFSLACK_BOT_TOKEN` is set as a secret and the token is valid                      |
| Messages go to the wrong channel          | Confirm the channel name in `nextflow_config` matches exactly (no `#` prefix, case-sensitive) |
| Slack notifications during local runs     | This should not happen — the plugin is only declared in the CI workflow's `nextflow_config`   |
| Token validation warning on startup       | The bot token may be expired or revoked — regenerate it in the Slack app settings             |

## Reference

- [nf-slack plugin documentation](https://seqeralabs.github.io/nf-slack/latest/)
- [nf-slack bot setup guide](https://seqeralabs.github.io/nf-slack/latest/getting-started/bot-setup/)
- [Seqera Platform launch action](https://github.com/seqeralabs/action-tower-launch)
