from pathlib import Path

from jinja2 import Template

from src.spps_cover.base_types import SPPS_ISSN, SppsMetadata

_ASSETS_DIR = Path(__file__).parent / "assets"

_COVER_TEMPLATE = Template(
    """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
@font-face {
  font-family: "STIX Two Text";
  font-style: normal;
  font-weight: 400;
  src: url("{{ font_regular_uri }}") format("truetype");
}
@font-face {
  font-family: "STIX Two Text";
  font-style: normal;
  font-weight: 700;
  src: url("{{ font_bold_uri }}") format("truetype");
}
@font-face {
  font-family: "STIX Two Text";
  font-style: italic;
  font-weight: 400;
  src: url("{{ font_italic_uri }}") format("truetype");
}
@page {
  size: A4;
  margin: 0;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  width: 210mm;
  height: 297mm;
  font-family: "STIX Two Text", "Times New Roman", Times, serif;
  color: #1a1a1a;
}
.page {
  width: 210mm;
  height: 297mm;
  padding: 30mm 25mm 25mm 25mm;
  display: flex;
  flex-direction: column;
}
.logo {
  margin-bottom: 14mm;
  text-align: center;
}
.logo img {
  height: 16mm;
  width: auto;
}
.series-title {
  font-size: 14pt;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 10mm;
  color: #333;
  text-align: center;
}
.number {
  font-size: 14pt;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #333;
  text-align: center;
  margin-bottom: 0;
}
.author {
  font-size: 14pt;
  font-weight: 500;
  margin-bottom: 6mm;
  line-height: 1.4;
}
.title {
  font-size: 20pt;
  font-weight: 700;
  margin-bottom: 6mm;
  line-height: 1.3;
}
.year {
  font-size: 14pt;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 0;
}
.spacer {
  flex: 1;
}
.cite-block {
  margin-bottom: 8mm;
}
.cite-label {
  font-size: 9pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #555;
  margin-bottom: 2mm;
}
.cite-content {
  font-size: 14pt;
  font-weight: 500;
  line-height: 1.4;
}
.cite-content a {
  color: #337ab7;
  text-decoration: none;
}
.footer-line {
  font-size: 9pt;
  color: #555;
  line-height: 1.6;
}
.footer-line a {
  color: #555;
  text-decoration: none;
}
</style>
</head>
<body>
<div class="page">
  <div class="logo">
    <img src="{{ logo_data_uri }}" alt="philosophie.ch">
  </div>

  <div class="series-title">Swiss Philosophical Preprint Series</div>
  <div class="number">No. {{ number }}</div>

  <div class="spacer"></div>

  <div class="author">{{ authors }}</div>

  <div class="title">{{ title }}</div>

  <div class="year">{{ date_year }}</div>

  <div class="spacer"></div>

  <div class="cite-block">
    <div class="cite-label">How to cite</div>
    <div class="cite-content">{{ how_to_cite_html }}</div>
  </div>

  <div class="footer-line">
    ISSN {{ issn }}<br>
    <a href="{{ license_url }}">{{ license_name }}</a><br>
    &copy; {{ copyright_holder }}
  </div>
</div>
</body>
</html>"""
)


def _data_uri(path: Path, mime: str) -> str:
    import base64

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_cover_html(metadata: SppsMetadata) -> str:
    return _COVER_TEMPLATE.render(
        logo_data_uri=_data_uri(_ASSETS_DIR / "logo-philo-ch-text-bigger.svg", "image/svg+xml"),
        font_regular_uri=_data_uri(_ASSETS_DIR / "STIXTwoText-Regular.ttf", "font/ttf"),
        font_bold_uri=_data_uri(_ASSETS_DIR / "STIXTwoText-Bold.ttf", "font/ttf"),
        font_italic_uri=_data_uri(_ASSETS_DIR / "STIXTwoText-Italic.ttf", "font/ttf"),
        number=metadata.number,
        authors=", ".join(metadata.authors),
        title=metadata.title,
        date_year=metadata.date_year,
        how_to_cite_html=metadata.how_to_cite_html,
        issn=SPPS_ISSN,
        license_name=metadata.license_name,
        license_url=metadata.license_url,
        copyright_holder=metadata.copyright_holder,
    )
