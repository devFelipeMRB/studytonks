"""Generate original book + rising chart icon. Pillow is a build-time tool only."""

from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / "app" / "assets"
root.mkdir(parents=True, exist_ok=True)
im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((8, 8, 248, 248), radius=58, fill="#D7EAFE")
d.rounded_rectangle((44, 55, 211, 205), radius=14, fill="#263B51")
d.rounded_rectangle((51, 48, 204, 190), radius=12, fill="#FAF9F6")
d.line((76, 69, 76, 173), fill="#659ED5", width=8)
d.line([(99, 153), (128, 128), (150, 139), (182, 91)], fill="#319B70", width=10)
d.polygon([(166, 89), (189, 83), (188, 109)], fill="#319B70")
im.save(root / "studytonks.png")
im.save(
    root / "studytonks.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
(root / "studytonks.svg").write_text(
    """<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect x="8" y="8" width="240" height="240" rx="58" fill="#D7EAFE"/><rect x="44" y="55" width="167" height="150" rx="14" fill="#263B51"/><rect x="51" y="48" width="153" height="142" rx="12" fill="#FAF9F6"/><path d="M76 69V173" stroke="#659ED5" stroke-width="8"/><path d="M99 153L128 128L150 139L182 91" fill="none" stroke="#319B70" stroke-width="10"/><path d="M166 89L189 83L188 109Z" fill="#319B70"/></svg>""",
    encoding="utf-8",
)
