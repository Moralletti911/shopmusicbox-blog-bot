#!/usr/bin/env python3
"""
ShopMusicBox Blog Post Bot
---------------------------
Generates SEO-optimized blog posts with OpenAI gpt-4o-mini and
publishes them to Shopify.

Self-managing schedule:
  article count < 30  → posts every day the workflow runs
  article count >= 30 → posts only on Mondays (weekly forever)

Run: python generate_post.py
"""

import os
import re
import sys
import datetime
import requests
from openai import OpenAI

# ─── Environment ──────────────────────────────────────────────────────────────
OPENAI_API_KEY       = os.environ["OPENAI_API_KEY"]
SHOPIFY_ACCESS_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_STORE_URL    = os.environ["SHOPIFY_STORE_URL"].rstrip("/")
SHOPIFY_BLOG_HANDLE  = os.environ.get("SHOPIFY_BLOG_HANDLE", "news")
AUTHOR_NAME          = os.environ.get("AUTHOR_NAME", "Admin")

MODEL       = "gpt-4o-mini"   # ~$0.01–0.05 per post
API_VERSION = "2024-01"

client = OpenAI(api_key=OPENAI_API_KEY)


# ─── Topic pool (35 topics, cycles in order) ──────────────────────────────────
TOPICS = [
    "Best Wooden Music Boxes for Newborns and Babies",
    "Music Box Gift Ideas for Birthdays (Any Age)",
    "How to Choose the Perfect Music Box Melody",
    "How Are Wooderful Life Music Boxes Made?",
    "Music Box Gifts for Anniversaries and Weddings",
    "Animal Music Boxes for Kids: A Buyer's Guide",
    "Best Music Boxes for Christmas Gifts This Year",
    "How to Care for and Clean a Wooden Music Box",
    "Music Boxes for Grandparents: Sentimental Gifts They'll Treasure",
    "What Melodies Can You Get in a Wooden Music Box?",
    "Music Box vs Snow Globe: Which Makes a Better Gift?",
    "Ocean and Beach Themed Music Boxes: Buyer's Guide",
    "Music Boxes for Baby Showers: The Complete Guide",
    "How Long Do Wooden Music Boxes Last?",
    "Fantasy Music Boxes: Unicorns, Castles, and Fairy Tales",
    "Music Box Gifts for Valentine's Day",
    "Classic Music Boxes: Timeless Gifts for Everyone",
    "How to Wind a Music Box (and Other Beginner Questions Answered)",
    "Music Box Display and Storage Ideas for Your Home",
    "Affordable Music Box Gifts Under $50",
    "Music Boxes for Mother's Day: What She'll Actually Love",
    "5 Things That Make a High-Quality Wooden Music Box",
    "Music Boxes for Graduation: Marking a Milestone with a Meaningful Gift",
    "How to Ship a Music Box Without Breaking It",
    "Music Boxes for Sympathy and Memorial Gifts",
    "Music Boxes for Retirement: Celebrating the Next Chapter",
    "Ballerina Music Boxes: A Complete Buyer's Guide",
    "Love-Themed Music Boxes: Romantic Gift Ideas",
    "Can You Customize the Song in a Music Box?",
    "Music Boxes for Father's Day: Unexpected Gift Ideas He'll Keep",
    "Christmas Music Boxes: Holiday Gifts Worth Giving",
    "Music Boxes for Kids: Age-by-Age Gift Guide",
    "The History of the Music Box (and Why It Still Makes the Perfect Gift)",
    "Music Box Gift Sets: What to Look For",
    "Why Wooden Music Boxes Make Better Gifts Than Plastic Ones",
]


# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the blog writer for ShopMusicBox.com, where we sell Wooderful Life wooden music boxes. These are handcrafted, beautifully designed music boxes that play a melody when wound by hand. Customers buy them as gifts for birthdays, anniversaries, baby showers, graduations, holidays, and everyday meaningful moments.

BRAND VOICE
Warm, genuine, and helpful. Like a knowledgeable friend who loves giving great gifts. Not corporate, not stiff, never pushy.

OUTPUT FORMAT — follow this exactly, no exceptions:
First line: TITLE: [your title, max 70 characters, SEO-friendly, no quotes]
Then immediately the HTML body (start right after the TITLE line).
After the HTML body, two final lines on their own:
META: [your 140-155 character meta description, starts with the primary keyword, no quotes]
TAGS: tag1, tag2, tag3 (2-4 tags, lowercase, relevant to music boxes and this post's topic)

HTML RULES
- Use only: <h2>, <p>, <ul>, <li>, <ol>, <strong>, <em>, <a href="...">
- No <h1> tags (the page title is handled separately)
- No inline styles, no divs, no tables, no class attributes
- Short paragraphs: 2 to 4 sentences max
- Total body word count: 700 to 950 words

SEO AND GEO RULES (every post must include all of these)
- First paragraph: directly answers the core question or search intent in 2-3 sentences, no warm-up, no fluff
- H2 headings: written as questions or exact phrases people type into Google ("How to...", "What is the best...", "Why...")
- At least one bulleted or numbered list
- Mention "ShopMusicBox.com" at least twice, naturally worked into the text
- End with exactly this FAQ block:
    <h2>Frequently Asked Questions</h2>
  Then 2-3 question/answer pairs:
    <h3>Question here?</h3>
    <p>Answer here.</p>

WRITING RULES
- Use contractions freely (you'll, it's, don't, that's, we're, they're)
- Write like a real person, not a content mill
- NEVER use em dashes (— or -) anywhere in the post — use a comma or rewrite the sentence
- NEVER use these words: delve, realm, comprehensive, it's worth noting, in conclusion, let's explore, seamlessly, robust, leverage, testament, game-changer, elevate, unleash
- Do NOT start any sentence with: Moreover, Furthermore, Additionally, In summary

FACTS YOU MUST NEVER GET WRONG
- Brand name is: Wooderful Life
- Store is: ShopMusicBox.com
- Products are handcrafted wooden music boxes (wound by hand, not battery-powered, not electronic)
- Collection themes available: Animals, Classic, Fantasy, Love, Ocean, Christmas
- Contact: hello@shopmusicbox.com"""


# ─── Shopify API helpers ──────────────────────────────────────────────────────
def shopify_headers():
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def get_blog_id(handle):
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/blogs.json"
    resp = requests.get(url, headers=shopify_headers(), timeout=15)
    resp.raise_for_status()
    blogs = resp.json().get("blogs", [])
    for blog in blogs:
        if blog["handle"] == handle:
            return blog["id"]
    available = [b["handle"] for b in blogs]
    raise ValueError(
        f"No blog found with handle '{handle}'. "
        f"Blogs available: {available}. "
        f"Update the SHOPIFY_BLOG_HANDLE secret to match one of these."
    )


def count_articles(blog_id):
    url = (
        f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}"
        f"/blogs/{blog_id}/articles/count.json"
    )
    resp = requests.get(url, headers=shopify_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()["count"]


def publish_article(blog_id, title, body_html, summary_html, tags):
    url = (
        f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}"
        f"/blogs/{blog_id}/articles.json"
    )
    payload = {
        "article": {
            "title"        : title,
            "author"       : AUTHOR_NAME,
            "body_html"    : body_html,
            "summary_html" : summary_html,
            "tags"         : ", ".join(tags) if isinstance(tags, list) else tags,
            "published"    : True,
        }
    }
    resp = requests.post(url, json=payload, headers=shopify_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()["article"]


# ─── Schedule logic ───────────────────────────────────────────────────────────
def should_post_today(article_count):
    if article_count < 30:
        return True, f"daily mode — building first 30 posts (currently at {article_count})"
    today = datetime.datetime.now(datetime.timezone.utc).weekday()   # 0 = Monday
    if today == 0:
        return True, f"weekly Monday mode — article count is {article_count}, posting today"
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return (
        False,
        f"weekly mode — today is {day_names[today]}, skipping (next post is Monday)"
    )


# ─── Topic selection ──────────────────────────────────────────────────────────
def pick_topic(article_count):
    """Cycle through topics in order based on how many posts exist."""
    return TOPICS[article_count % len(TOPICS)]


# ─── Content generation ───────────────────────────────────────────────────────
def generate_post(topic):
    user_message = (
        f"Write a blog post for ShopMusicBox.com about: {topic}\n\n"
        "Follow ALL rules in your system instructions exactly, including the output format."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.7,
        max_tokens=1800,
    )
    return response.choices[0].message.content.strip()


def parse_response(raw, fallback_title):
    """
    Expects output in this shape:
        TITLE: The title here
        <h2>First heading</h2>
        <p>Body...</p>
        ...
        META: 140-155 char meta description
        TAGS: tag1, tag2, tag3
    """
    lines = raw.strip().split("\n")

    # Title from first line
    title = fallback_title
    body_start = 0
    if lines and lines[0].upper().startswith("TITLE:"):
        title = lines[0].split(":", 1)[1].strip().strip('"\'')
        body_start = 1

    # META and TAGS from end of text
    meta_match = re.search(r"^META:\s*(.+)$", raw, re.MULTILINE)
    tags_match = re.search(r"^TAGS:\s*(.+)$", raw, re.MULTILINE)

    meta     = meta_match.group(1).strip().strip('"\'') if meta_match else ""
    tags_raw = tags_match.group(1).strip() if tags_match else ""
    tags     = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]

    # Body: everything after title, before META line
    body_text = "\n".join(lines[body_start:])
    for marker in ("\nMETA:", "\nTAGS:"):
        pos = body_text.rfind(marker)
        if pos != -1:
            body_text = body_text[:pos]
    body_text = body_text.strip()

    # Hard safety net: remove em dashes even if the model sneaks them in
    body_text = (
        body_text
        .replace("—", ",")   # —
        .replace("–", ",")   # –
        .replace("&mdash;", ",")
        .replace("&ndash;", ",")
    )

    return title, body_text, meta, tags


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("ShopMusicBox Blog Bot")
    print(f"Timestamp : {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # 1. Get blog ID
    print(f"\n[1/4] Looking up blog '{SHOPIFY_BLOG_HANDLE}'...")
    blog_id = get_blog_id(SHOPIFY_BLOG_HANDLE)
    print(f"      Blog ID: {blog_id}")

    # 2. Check schedule
    print("\n[2/4] Checking schedule...")
    article_count = count_articles(blog_id)
    posting, reason = should_post_today(article_count)
    print(f"      {reason}")

    if not posting:
        print("\nNothing to post today. Exiting cleanly.")
        print("=" * 60)
        sys.exit(0)

    # 3. Generate post
    topic = pick_topic(article_count)
    print(f"\n[3/4] Generating post...")
    print(f"      Topic : {topic}")

    raw = generate_post(topic)
    title, body_html, meta, tags = parse_response(raw, fallback_title=topic)

    print(f"      Title : {title}")
    print(f"      Meta  : {meta[:80]}{'...' if len(meta) > 80 else ''} ({len(meta)} chars)")
    print(f"      Tags  : {tags}")
    print(f"      Body  : {len(body_html)} characters")

    # 4. Publish
    print("\n[4/4] Publishing to Shopify...")
    article = publish_article(
        blog_id,
        title,
        body_html,
        f"<p>{meta}</p>",
        tags,
    )

    print("\n" + "=" * 60)
    print("  Published!")
    print(f"  Article ID : {article['id']}")
    print(f"  Title      : {article['title']}")
    print(f"  Public URL : https://{SHOPIFY_STORE_URL}/blogs/{SHOPIFY_BLOG_HANDLE}/{article['handle']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
