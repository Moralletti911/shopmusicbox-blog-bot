# ShopMusicBox Blog Bot

Automatically generates and publishes SEO-optimized blog posts to ShopMusicBox.com using OpenAI and GitHub Actions. No servers, no databases, no monthly fees beyond OpenAI usage (roughly $0.01 to $0.05 per post).

## What it does

Runs daily via GitHub Actions at 9 AM EST. Picks a topic from a pool of 35, generates a 700-950 word post with OpenAI gpt-4o-mini, and publishes it live to Shopify.

Self-managing schedule:
- **First 30 posts:** publishes every day
- **After 30 posts:** publishes Mondays only, forever

## Required GitHub Secrets

Go to your repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value to enter |
|---|---|
| `OPENAI_API_KEY` | Your key from platform.openai.com/api-keys |
| `SHOPIFY_ACCESS_TOKEN` | The `shpat_...` token from your Shopify Custom App |
| `SHOPIFY_STORE_URL` | `shopmusicbox.com` (no https://, no trailing slash) |
| `SHOPIFY_BLOG_HANDLE` | The handle of your blog, e.g. `news` or `blog` |
| `AUTHOR_NAME` | Author name for posts, e.g. `ShopMusicBox Team` |

## Trigger manually

1. Go to the **Actions** tab in this repo
2. Click **Post Blog Article** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Click into the running job and watch the log
5. A successful run ends with: `Published! Article ID: ...`

## Where posts appear

- **Shopify Admin:** Online Store → Blog Posts
- **Live URL:** `https://shopmusicbox.com/blogs/[your-blog-handle]`

## Adding the blog link to your Shopify navigation

After you create the blog in Shopify Admin, add it to your menus here:
- **Online Store → Navigation → Footer menu** (add "Blog" linking to `/blogs/news`)
- **Online Store → Navigation → Main menu** (optional — add between Collections and Search)
