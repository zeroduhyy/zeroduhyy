import requests
import argparse
import base64
import io
import textwrap
import random
from PIL import Image, ImageOps  # pillow required

API_URL = "https://graphql.anilist.co"
FAV_QUERY = """
query ($userName: String) {
  User(name: $userName) {
    favourites {
      anime {
        nodes {
          id
          title { romaji }
          coverImage { large, medium }
          siteUrl
        }
      }
    }
  }
}
"""

# ---------- helper functions ----------
def fetch_favorites(username, proxies_disable=True, timeout=15):
    kwargs = {}
    if proxies_disable:
        kwargs["proxies"] = {"http": None, "https": None}
    res = requests.post(API_URL, json={"query": FAV_QUERY, "variables": {"userName": username}}, timeout=timeout, **kwargs)
    res.raise_for_status()
    js = res.json()
    if "errors" in js:
        raise RuntimeError("AniList API returned errors: " + str(js["errors"]))
    nodes = js["data"]["User"]["favourites"]["anime"]["nodes"]
    return nodes

def download_image_to_bytes(url, proxies_disable=True, timeout=20):
    kwargs = {}
    if proxies_disable:
        kwargs["proxies"] = {"http": None, "https": None}
    r = requests.get(url, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r.content

def image_bytes_to_data_uri(img_bytes, mime="image/jpeg"):
    b64 = base64.b64encode(img_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"

def ensure_image_size_and_pad(img_bytes, target_w, target_h):
    # use PIL to resize while keeping aspect and pad to target size
    im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    im.thumbnail((target_w, target_h), Image.LANCZOS)
    # center on background
    bg = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
    x = (target_w - im.width) // 2
    y = (target_h - im.height) // 2
    bg.paste(im, (x,y), im)
    out = io.BytesIO()
    bg.convert("RGBA").save(out, format="PNG")
    return out.getvalue()

def escape_xml(s):
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

# ---------- SVG generator ----------
def generate_svg(card_items, out_file="favorites.svg",
                 cols=5, img_w=160, img_h=220, padding=18, title_fontsize=14,
                 bg_color="#071126", text_color="#e8f6ff", card_radius=8, gap=18):
    # card_items: list of dicts: {'title','img_data_uri','url'}
    rows = (len(card_items) + cols - 1) // cols
    width = padding*2 + cols*img_w + (cols-1)*gap
    # allow space for titles
    title_area_h = 40
    height = padding*2 + rows*(img_h + title_area_h) + (rows-1)*gap

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    # background
    svg.append(f'<rect width="100%" height="100%" rx="12" fill="{bg_color}" />')
    # title header
    svg.append(f'<text x="{padding}" y="{padding - 2}" font-family="Inter, Noto Sans, Arial" font-size="18" fill="{text_color}">❤ My AniList Favorites</text>')

    for idx, item in enumerate(card_items):
        col = idx % cols
        row = idx // cols
        x = padding + col * (img_w + gap)
        y = padding + row * (img_h + title_area_h + gap)

        # card background
        svg.append(f'<g>')
        svg.append(f'  <rect x="{x}" y="{y}" width="{img_w}" height="{img_h+title_area_h}" rx="{card_radius}" fill="rgba(255,255,255,0.03)"/>')

        # image (embedded)
        svg.append(f'  <image x="{x}" y="{y}" width="{img_w}" height="{img_h}" href="{item["img_data_uri"]}" preserveAspectRatio="xMidYMid slice"/>')

        # title (wrap to two lines)
        title = item["title"]
        maxchars = 22  # heuristic
        lines = textwrap.wrap(title, maxchars)
        if len(lines) > 2:
            lines = lines[:2]
            # append ellipsis
            if len(lines[1]) > 3:
                lines[1] = lines[1][:-3] + "..."
        # draw title lines (centered under the image)
        title_cx = x + img_w / 2
        title_y = y + img_h +18
        svg.append(f'  <a href="{escape_xml(item["url"])}" target="_blank">')
        for li, line in enumerate(lines):
            ty = title_y + li * (title_fontsize + 2)
            # use text-anchor="middle" to center the text at title_cx
            svg.append(f'    <text x="{title_cx}" y="{ty}" text-anchor="middle" font-family="Inter, Noto Sans, Arial" font-size="{title_fontsize}" fill="{text_color}">{escape_xml(line)}</text>')
        svg.append('  </a>')
        svg.append('</g>')

    svg.append('</svg>')
    svg_content = "\n".join(svg)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"✅ SVG saved to {out_file} (size: {len(svg_content):,} bytes)")

# ---------- main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", "-u", required=True, help="AniList username")
    parser.add_argument("--out", "-o", default="favorites.svg", help="Output SVG file")
    parser.add_argument("--n", "-n", type=int, default=10, help="How many favorites to include (max)")
    parser.add_argument("--cols", type=int, default=5, help="Columns")
    parser.add_argument("--disable-proxy", action="store_true", help="Disable proxies (recommended if you saw ProxyError)")
    args = parser.parse_args()

    print("Fetching favorites from AniList for user:", args.user)
    try:
        nodes = fetch_favorites(args.user, proxies_disable=args.disable_proxy)
    except Exception as e:
        print("❌ Error fetching favorites:", e)
        return

    items = []
    # pick random sample of favorites (up to n)
    selected = random.sample(nodes, k=min(args.n, len(nodes)))
    for node in selected:
        title = node.get("title", {}).get("romaji") or node.get("title", {}).get("english") or "Unknown"
        # prefer large, fallback to medium
        cover = node.get("coverImage", {}).get("large") or node.get("coverImage", {}).get("medium")
        url = node.get("siteUrl") or f"https://anilist.co/anime/{node.get('id')}"
        if not cover:
            print(" - skip (no cover):", title)
            continue
        try:
            # download, resize-pad to consistent size and convert to PNG data uri
            raw = download_image_to_bytes(cover, proxies_disable=args.disable_proxy)
            png_bytes = ensure_image_size_and_pad(raw, target_w=400, target_h=560)  # larger to keep quality; SVG will scale
            data_uri = image_bytes_to_data_uri(png_bytes, mime="image/png")
            items.append({"title": title, "img_data_uri": data_uri, "url": url})
            print(" +", title)
        except Exception as e:
            print(" ! failed to download image for:", title, "error:", e)

    if not items:
        print("❌ No items collected, aborting.")
        return

    # generate SVG with scaled-down image sizes for display
    generate_svg(items, out_file=args.out, cols=args.cols, img_w=160, img_h=220)

if __name__ == "__main__":
    main()
