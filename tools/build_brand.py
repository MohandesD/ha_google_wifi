"""Render the project's original geometric mark; no Google artwork is used."""

from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
destination = root / "custom_components/google_wifi_insights/brand"
destination.mkdir(exist_ok=True)
svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
<rect x="8" y="8" width="240" height="240" rx="48" fill="#142b45"/>
<g fill="none" stroke="#68cfff" stroke-width="12" stroke-linecap="round">
<path d="M67.19 106.19 A86 86 0 0 1 188.81 106.19"/>
<path d="M85.57 124.57 A60 60 0 0 1 170.43 124.57"/>
<path d="M103.96 142.96 A34 34 0 0 1 152.04 142.96"/>
</g><circle cx="128" cy="167" r="9" fill="#fff"/>
<path d="M77 210 H179" stroke="#fff" stroke-width="5"/>
<g fill="#fff"><circle cx="77" cy="210" r="7"/><circle cx="128" cy="210" r="7"/><circle cx="179" cy="210" r="7"/></g>
</svg>
'''
(destination / "icon.svg").write_text(svg, encoding="utf-8", newline="\n")
for size, filename in ((256, "icon.png"), (512, "icon@2x.png")):
    image = Image.new("RGBA", (size * 2, size * 2))
    draw = ImageDraw.Draw(image)
    factor = size / 128

    def box(values):
        return tuple(round(value * factor) for value in values)

    draw.rounded_rectangle(box((8, 8, 248, 248)), radius=round(48 * factor), fill="#142b45")
    for radius in (86, 60, 34):
        draw.arc(box((128-radius, 167-radius, 128+radius, 167+radius)), 225, 315,
                 fill="#68cfff", width=round(12 * factor))
    draw.ellipse(box((119, 158, 137, 176)), fill="white")
    draw.line(box((77, 210, 179, 210)), fill="white", width=round(5 * factor))
    for x in (77, 128, 179):
        draw.ellipse(box((x-7, 203, x+7, 217)), fill="white")
    image.resize((size, size), Image.Resampling.LANCZOS).save(destination / filename, optimize=True)
print("Generated original local brand assets at 256 and 512 pixels.")
