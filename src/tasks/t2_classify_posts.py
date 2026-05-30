"""
T2: icin Hacker News gonderialtilerlesatiranakonupuansinifvesicaknoktatani

gorebaslikvekaynak, karar verheryazigonderialtcekirdekalan, veisaretsicakkapigonderialt. 
"""

from dataclasses import dataclass

from .t1_extract_posts import Post

# tanimpuansinifsinifayri
CATEGORIES = {
    "hardware": ["steam controller", "hardware", "chip", "gpu", "cpu", "console"],
    "ai_ml": [
        "llm",
        "ai",
        "machine learning",
        "deep learning",
        "model",
        "agent",
        "gpt",
        "neural",
    ],
    "open_source": ["open source", "github", "creative commons", "license", "release"],
    "programming": [
        "programming",
        "coding",
        "software",
        "developer",
        "code",
        "api",
        "framework",
    ],
    "security": ["security", "privacy", "hack", "vulnerability", "fraud", "defense"],
    "web_dev": ["web", "css", "html", "javascript", "frontend", "backend", "http"],
    "startup_business": ["startup", "yc", "hiring", "business", "company", "funding"],
    "science": ["science", "research", "biology", "physics", "math", "cell"],
    "culture_life": [
        "culture",
        "life",
        "workplace",
        "productivity",
        "british",
        "sorry",
        "pen pal",
    ],
    "gaming": ["game", "gaming", "steam", "controller"],
    "cloud_infra": [
        "cloud",
        "infrastructure",
        "diskless",
        "pxe",
        "zfs",
        "iscsi",
        "server",
    ],
    "transportation": ["car", "camper", "van", "subway", "nyc", "transport"],
}


def classify_post(post: Post) -> list[str]:
    """
    icintekilogregonderialtilerlesatirpuansinif. 

    Args:
        post: isterpuansinifgonderialt. 

    Returns:
        bugonderialtozelliksinifayriliste (birgonderialtolabiliredebilirozellikdecoksinifayri) . 
    """
    title_lower = post.title.lower()
    source_lower = post.source.lower()
    text = f"{title_lower} {source_lower}"

    matched_categories = []
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in text:
                matched_categories.append(category)
                break

    if not matched_categories:
        matched_categories.append("other")

    return matched_categories


@dataclass
class ClassificationResult:
    """puansinifsonuc"""

    posts: list[Post]
    categories: dict[str, list[Post]]
    hot_posts: list[Post]  # noktabegenisayi > 500 veyayorumsayi > 200


def classify_all_posts(posts: list[Post]) -> ClassificationResult:
    """
    icinvargonderialtilerlesatirpuansinifvetanisicakkapikonusmakonu. 

    Args:
        posts: vargonderialtliste. 

    Returns:
        icerirpuansinifsonucvesicakkapigonderialticinnesne. 
    """
    categories: dict[str, list[Post]] = {}
    hot_posts: list[Post] = []

    for post in posts:
        # puansinif
        matched = classify_post(post)
        for cat in matched:
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(post)

        # sicakkapitani
        if post.points > 500 or post.comments > 200:
            hot_posts.append(post)

    return ClassificationResult(posts=posts, categories=categories, hot_posts=hot_posts)


def print_classification(result: ClassificationResult) -> None:
    """yazdirpuansinifsonuc"""
    print("=== puansinifsonuc ===\n")

    for category, posts in sorted(result.categories.items()):
        print(f"\n--- {category} ({len(posts)} ogre) ---")
        for post in posts:
            print(f"  {post.rank}. {post.title}")

    print("\n\n=== sicakkapikonusmakonu (noktabegeni > 500 veyayorum > 200) ===\n")
    for post in result.hot_posts:
        print(
            f"  {post.rank}. {post.title} (noktabegeni: {post.points}, yorum: {post.comments})"
        )


if __name__ == "__main__":
    # testpuansinif
    from .t1_extract_posts import extract_posts

    test_content = """
1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )
1505 points by haunter 20 hours ago | hide | 496 comments
2. Appearing productive in the workplace ( nooneshappy.com )
1273 points by diebillionaires 19 hours ago | hide | 504 comments
3. Boris Cherny: TI-83 Plus Basic Programming Tutorial (2004) ( ticalc.org )
42 points by suoken 4 hours ago | hide | 16 comments
"""
    posts = extract_posts(test_content)
    result = classify_all_posts(posts)
    print_classification(result)
