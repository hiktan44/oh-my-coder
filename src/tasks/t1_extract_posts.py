"""
T1: cikar Hacker News ilksayfagonderialtbilgi

saglaragsayfaicerikicindecikarvar30ogregonderialtyapibilgi. 
"""

from dataclasses import dataclass


@dataclass
class Post:
    """tablogoster Hacker News ustbirogregonderialt"""

    rank: int
    title: str
    source: str
    points: int
    author: str
    time_ago: str
    comments: int
    url: str = ""


def extract_posts(raw_content: str) -> list[Post]:
    """
    hamagsayfaicerikicindecikargonderialtliste. 

    Args:
        raw_content:  Hacker News ilksayfayakalaalmetinicerik. 

    Returns:
        icerirvargonderialtliste. 
    """
    posts: list[Post] = []
    lines = raw_content.strip().split("\n")

    current_rank = 0
    current_title = ""
    current_source = ""
    current_points = 0
    current_author = ""
    current_time = ""
    current_comments = 0
    current_url = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # eslestirgonderialtogrehedef, format: "sirano. baslik ( kaynak )"
        # ornekornegin: "1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )"
        import re

        match = re.match(r"^(\d+)\.\s+(.+?)\s+\((.+?)\)\s*$", line)
        if match:
            # egervarustbirgonderialt, kaydet
            if current_title:
                posts.append(
                    Post(
                        rank=current_rank,
                        title=current_title,
                        source=current_source,
                        points=current_points,
                        author=current_author,
                        time_ago=current_time,
                        comments=current_comments,
                        url=current_url,
                    )
                )

            # yenigonderialttemelbilgi
            current_rank = int(match.group(1))
            current_title = match.group(2).strip()
            current_source = match.group(3).strip()
            current_points = 0
            current_author = ""
            current_time = ""
            current_comments = 0
            current_url = ""
            continue

        # eslestirnoktabegenisayi, yazar, zamanarasinda, yorumsayisatir
        # format: "1505 points by haunter 20 hours ago | hide | 496 comments"
        points_match = re.match(
            r"^(\d+)\s+points\s+by\s+(\S+)\s+(.+?)\s+\|\s+hide\s+\|\s+(\d+)\s+comments$",
            line,
        )
        if points_match and current_rank:
            current_points = int(points_match.group(1))
            current_author = points_match.group(2)
            current_time = points_match.group(3).strip()
            current_comments = int(points_match.group(4))
            continue

    # kaydetensonrabirogregonderialt
    if current_title:
        posts.append(
            Post(
                rank=current_rank,
                title=current_title,
                source=current_source,
                points=current_points,
                author=current_author,
                time_ago=current_time,
                comments=current_comments,
                url=current_url,
            )
        )

    return posts


def print_posts(posts: list[Post]) -> None:
    """yazdirgonderialtliste"""
    print(f"ortakcikar {len(posts)} ogregonderialt:\n")
    for post in posts:
        print(f"{post.rank}. {post.title}")
        print(
            f"   kaynak: {post.source} | noktabegeni: {post.points} | yazar: {post.author} | {post.time_ago} | yorum: {post.comments}"
        )
        print()


if __name__ == "__main__":
    # testcikar
    test_content = """1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )
1505 points by haunter 20 hours ago | hide | 496 comments"""

    posts = extract_posts(test_content)
    print_posts(posts)
