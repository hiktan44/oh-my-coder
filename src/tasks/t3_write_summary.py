"""
T3: Hacker News ana sayfa icerik ozeti yaz

Puan siniflandirma sonuclarina dayanarak 200-300 kelimelik dogal dil ozeti olustur.
"""

from .t1_extract_posts import extract_posts
from .t2_classify_posts import ClassificationResult, classify_all_posts


def generate_summary(result: ClassificationResult) -> str:
    """
    Puan siniflandirma sonucundan ozet olustur.

    Args:
        result: Puan siniflandirma sonuc nesnesi.

    Returns:
        200-300 kelimelik ozet metin.
    """
    hot_posts = result.hot_posts
    categories = result.categories

    # En populer gonderiyi bul
    top_post = hot_posts[0] if hot_posts else result.posts[0]
    second_post = hot_posts[1] if len(hot_posts) > 1 else None

    # Her kategorideki gonderi sayisini say
    category_counts = {cat: len(posts) for cat, posts in categories.items()}
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[
        :3
    ]

    # Ozet olustur
    summary_parts = []

    # Giris: genel tanitim
    summary_parts.append(
        f"Hacker News ana sayfasi bugun {len(result.posts)} populer teknoloji haberi sunuyor, "
        f"donanim, AI, acik kaynak, programlama, guvenlik vb. bircok alani kapsiyor. "
    )

    # cekirdeksicakkapikonusmakonu
    if top_post:
        summary_parts.append(
            f"en cok dikkat ceken: '{top_post.title}'"
            f" (kaynak: {top_post.source}), "
            f"{top_post.points} begeni ve {top_post.comments} yorum aldi, "
            f"bugunun odak noktasi oldu. "
        )

    if second_post:
        summary_parts.append(
            f"hemen ardindan: '{second_post.title}'"
            f" (kaynak: {second_post.source}), "
            f"toplulukta benzer ilgi gordu. "
        )

    # Kategori dagilimi
    if top_categories:
        cat_names = {
            "hardware": "donanim",
            "ai_ml": "AI/makine ogrenmesi",
            "open_source": "acik kaynak",
            "programming": "programlama",
            "security": "guvenlik",
            "web_dev": "Web gelistirme",
            "startup_business": "girisim/is",
            "science": "bilim",
            "culture_life": "kultur/yasam",
            "gaming": "oyun",
            "cloud_infra": "bulut altyapi",
            "transportation": "ulasim",
        }
        category_text = ", ".join(
            f"{cat_names.get(cat, cat)} ({count} adet) "
            for cat, count in top_categories[:3]
        )
        summary_parts.append(f"Tema dagilimina bakildiginda, {category_text} bugunun en aktif tartisma alanlaridir. ")

    # Ilginc kesifler
    unique_posts = [p for p in result.posts if p not in hot_posts and p.points > 100]
    if unique_posts:
        interesting = unique_posts[0]
        summary_parts.append(
            f"Ilginc bir oge: '{interesting.title}'"
            f" (kaynak: {interesting.source}), "
            f"siralamada yuksek olmasa da {interesting.points} begeni aldi, "
            f"dikkate deger. "
        )

    # Genel egilim
    ai_related = len(categories.get("ai_ml", []))
    if ai_related > 3:
        summary_parts.append(
            "Genel olarak, AI ve programlama konulari hakim olmaya devam ediyor, "
            "teknoloji toplulugunun en son araclara ve gelistirme verimligine olan ilgisini yansitiyor. "
        )

    return "".join(summary_parts)


def main(raw_content: str) -> str:
    """
    Ana fonksiyon: cikar, puanla, siniflandir, ozetle.

    Args:
        raw_content: Hacker News ana sayfasi ham metin icerigi.

    Returns:
        Nihai ozet metni.
    """
    posts = extract_posts(raw_content)
    result = classify_all_posts(posts)
    summary = generate_summary(result)
    return summary


if __name__ == "__main__":
    # Saglanan web sayfasi icerigi ile test calistir
    test_content = """1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )
1505 points by haunter 20 hours ago | hide | 496 comments
2. Appearing productive in the workplace ( nooneshappy.com )
1273 points by diebillionaires 19 hours ago | hide | 504 comments
3. Boris Cherny: TI-83 Plus Basic Programming Tutorial (2004) ( ticalc.org )
42 points by suoken 4 hours ago | hide | 16 comments
4. SQLite Is a Library of Congress Recommended Storage Format ( sqlite.org )
335 points by whatisabcdefgh 14 hours ago | hide | 89 comments
5. Permacomputing Principles ( permacomputing.net )
170 points by andsoitis 9 hours ago | hide | 83 comments
6. GovernGPT (YC W24) Is Hiring Engineers to Build Thinking Systems in Montreal ( ycombinator.com )
6 minutes ago | hide
7. Agent-harness-kit scaffolding for multi-agent workflows (MCP, provider-agnostic) ( cardor.dev )
12 points by enmanuelmag 1 hour ago | hide | 3 comments
8. ZAYA1-8B: An 8B Moe Model with 760M Active Params Matching DeepSeek-R1 on Math ( firethering.com )
32 points by steveharing1 3 hours ago | hide | 25 comments
9. Diskless Linux boot using ZFS, iSCSI and PXE ( aniket.foo )
113 points by stereo-highway 8 hours ago | hide | 58 comments
10. Photoshop's challenges with focus, pt. 2 ( aresluna.org )
67 points by frizlab 5 hours ago | hide | 20 comments
11. LinkedIn profile visitor lists belong to the people, says Noyb ( theregister.com )
21 points by robin_reala 58 minutes ago | hide | 4 comments
12. Vibe coding and agentic engineering are getting closer than I'd like ( simonwillison.net )
635 points by e12e 21 hours ago | hide | 694 comments
13. Chevrolet Performance eCrate package (400v/200hp) ( chevrolet.com )
67 points by mindcrime 7 hours ago | hide | 43 comments
14. SingleRide: Longest route on NYC Subway without visiting the same station twice ( singleride.nyc )
30 points by TMWNN 5 hours ago | hide | 11 comments
15. RSS feeds send me more traffic than Google ( shkspr.mobi )
143 points by SpyCoder77 11 hours ago | hide | 31 comments
16. Show HN: Trust – Coding Rust like it's 1989 ( github.com/wojtczyk )
43 points by wojtczyk 6 hours ago | hide | 14 comments
17. ProgramBench: Can Language Models Rebuild Programs from Scratch? ( arxiv.org )
70 points by jonbaer 8 hours ago | hide | 39 comments
18. Indian matchbox labels as a visual archive ( itsnicethat.com )
10 points by sahar_builds 2 hours ago | hide | 1 comment
19. Making LLM Training Faster with Unsloth and NVIDIA ( unsloth.ai )
64 points by segmenta 4 hours ago | hide | 10 comments
20. The brave souls who bought a used, 340k-mile rental camper van ( thedrive.com )
13 points by PaulHoule 3 hours ago | hide | 5 comments
21. Google Cloud fraud defense, the next evolution of reCAPTCHA ( cloud.google.com )
328 points by unforgivenpasta 18 hours ago | hide | 329 comments
22. Show HN: Agent-skills-eval – Test whether Agent Skills improve outputs ( github.com/darkrishabh )
32 points by darkrishabh 5 hours ago | hide | 9 comments
23. From local to global: scaling governance for AI ( nature.com )\n15 points by ai_governance 30 minutes ago | hide | 2 comments\n"""

    result = classify_all_posts(extract_posts(test_content))
    summary = generate_summary(result)
    print(summary)
