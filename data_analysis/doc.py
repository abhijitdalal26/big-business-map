"""A tiny document builder that renders the same content to Markdown and HTML.

The study pack has to be readable in two places: a plain-text Markdown file the
author can quote from, and a self-contained HTML file that shows the charts
inline. Rather than write the content twice (and risk the two versions
drifting), every section is recorded once as a list of blocks and rendered
lazily to either format.

Block types
-----------
``h1`` ``h2`` ``h3``  headings
``p``                   paragraph (inline markdown-ish emphasis allowed)
``bullets``             list of strings
``table``               ``{"columns": [...], "rows": [[...], ...], "caption": str}``
``image``               ``{"path": "charts/01_x.png", "caption": str}``
``kv``                  list of ``(label, value)`` pairs rendered as a table
``note``                a callout paragraph
``code``                preformatted block
"""

from __future__ import annotations

import html as _html
import re
from typing import Any


# --------------------------------------------------------------------------- #
# inline formatting
# --------------------------------------------------------------------------- #
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`(.+?)`")
_ITAL = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _md_inline(text: str) -> str:
    """Escape the pipe character so markdown tables survive inline code."""
    return text.replace("|", "\\|")


def _html_inline(text: str) -> str:
    s = _html.escape(str(text))
    s = _CODE.sub(r"<code>\1</code>", s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITAL.sub(r"<em>\1</em>", s)
    return s


def _md_inline_keep(text: str) -> str:
    """Markdown flavour: keep ** and * but escape pipes."""
    return _md_inline(text)


# --------------------------------------------------------------------------- #
# document
# --------------------------------------------------------------------------- #
class Doc:
    """Accumulates content blocks and renders them to Markdown or HTML."""

    def __init__(self, title: str = "") -> None:
        self.title = title
        self.blocks: list[tuple[str, Any]] = []

    # -- writers ---------------------------------------------------------- #
    def h1(self, text: str) -> "Doc":
        self.blocks.append(("h1", text))
        return self

    def h2(self, text: str) -> "Doc":
        self.blocks.append(("h2", text))
        return self

    def h3(self, text: str) -> "Doc":
        self.blocks.append(("h3", text))
        return self

    def p(self, text: str) -> "Doc":
        self.blocks.append(("p", text))
        return self

    def bullets(self, items: list[str]) -> "Doc":
        self.blocks.append(("bullets", list(items)))
        return self

    def note(self, text: str) -> "Doc":
        self.blocks.append(("note", text))
        return self

    def code(self, text: str) -> "Doc":
        self.blocks.append(("code", text))
        return self

    def kv(self, pairs: list[tuple[str, str]]) -> "Doc":
        self.blocks.append(("kv", list(pairs)))
        return self

    def table(self, columns: list[str], rows: list[list[Any]],
              caption: str = "") -> "Doc":
        self.blocks.append(("table", {
            "columns": list(columns), "rows": [list(r) for r in rows],
            "caption": caption,
        }))
        return self

    def image(self, path: str, caption: str = "") -> "Doc":
        self.blocks.append(("image", {"path": path, "caption": caption}))
        return self

    def page_break(self) -> "Doc":
        self.blocks.append(("pagebreak", None))
        return self

    # -- renderers -------------------------------------------------------- #
    def to_markdown(self) -> str:
        out: list[str] = []
        for kind, payload in self.blocks:
            if kind == "h1":
                out.append(f"# {payload}")
            elif kind == "h2":
                out.append(f"\n## {payload}")
            elif kind == "h3":
                out.append(f"\n### {payload}")
            elif kind == "p":
                out.append(f"\n{payload}")
            elif kind == "note":
                out.append(f"\n> {payload}")
            elif kind == "bullets":
                for it in payload:
                    out.append(f"- {it}")
            elif kind == "code":
                out.append("\n```\n" + payload + "\n```")
            elif kind == "kv":
                rows = [[k, v] for k, v in payload]
                out.append("\n| | |")
                out.append("|---|---|")
                for k, v in rows:
                    out.append(f"| **{_md_inline_keep(str(k))}** | "
                               f"{_md_inline_keep(str(v))} |")
            elif kind == "table":
                out.append("")
                if payload["caption"]:
                    out.append(f"**{payload['caption']}**")
                    out.append("")
                out.append("| " + " | ".join(
                    _md_inline_keep(str(c)) for c in payload["columns"]) + " |")
                out.append("|" + "|".join(["---"] * len(payload["columns"])) + "|")
                for r in payload["rows"]:
                    out.append("| " + " | ".join(
                        _md_inline_keep("" if c is None else str(c))
                        for c in r) + " |")
            elif kind == "image":
                out.append("")
                out.append(f"![{payload['caption']}]({payload['path']})")
                if payload["caption"]:
                    out.append(f"*{payload['caption']}*")
            elif kind == "pagebreak":
                out.append("\n---\n")
        return "\n".join(out).strip() + "\n"

    # -- html shell -------------------------------------------------------- #
    HTML_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --ink:#0B2545; --bar:#1B6CA8; --accent:#E07A4F; --muted:#9AA5B1;
    --grid:#E6EAF0; --paper:#FFFFFF; --soft:#F6F8FB; --edge:#D8E0EA;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--soft); color:#12283f;
    font:16px/1.65 "Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
  }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:40px 28px 90px; }}
  header.hero {{
    background:var(--ink); color:#fff; padding:52px 40px; border-radius:14px;
    margin-bottom:34px;
  }}
  header.hero h1 {{ margin:0 0 8px; font-size:34px; letter-spacing:-0.4px; }}
  header.hero p {{ margin:0; color:#BFD3E4; font-size:15px; max-width:760px; }}
  .toc {{
    background:var(--paper); border:1px solid var(--edge); border-radius:12px;
    padding:20px 26px; margin-bottom:34px; columns:2; column-gap:38px;
  }}
  .toc h2 {{ margin:0 0 10px; font-size:13px; letter-spacing:1.4px;
             text-transform:uppercase; color:var(--muted); border:0; padding:0; }}
  .toc a {{ display:block; color:var(--bar); text-decoration:none;
            font-size:14.5px; padding:3px 0; break-inside:avoid; }}
  .toc a:hover {{ color:var(--accent); }}
  section {{
    background:var(--paper); border:1px solid var(--edge); border-radius:12px;
    padding:30px 34px; margin-bottom:26px;
  }}
  h1 {{ font-size:30px; color:var(--ink); border-bottom:3px solid var(--accent);
        padding-bottom:10px; margin:0 0 18px; }}
  h2 {{ font-size:21px; color:var(--ink); margin:34px 0 12px;
        border-left:4px solid var(--bar); padding-left:11px; }}
  h3 {{ font-size:16.5px; color:var(--bar); margin:24px 0 8px;
        text-transform:uppercase; letter-spacing:.6px; }}
  p {{ margin:0 0 14px; }}
  ul {{ margin:0 0 16px; padding-left:22px; }}
  li {{ margin-bottom:8px; }}
  blockquote {{
    margin:0 0 16px; padding:12px 18px; background:#FFF6F1;
    border-left:4px solid var(--accent); color:#6a3b26; border-radius:0 8px 8px 0;
  }}
  table {{ border-collapse:collapse; width:100%; margin:6px 0 20px; font-size:14px; }}
  th, td {{ border-bottom:1px solid var(--grid); padding:8px 11px;
            text-align:left; vertical-align:top; }}
  th {{ background:var(--soft); color:var(--ink); font-weight:600;
        border-bottom:2px solid var(--edge); }}
  tr:hover td {{ background:#FBFCFE; }}
  td strong {{ color:var(--ink); }}
  figure {{ margin:8px 0 24px; }}
  figure img {{ width:100%; border:1px solid var(--edge); border-radius:9px;
                display:block; background:#fff; }}
  figcaption {{ color:#5A6673; font-size:13.5px; margin-top:7px; }}
  code {{ background:var(--soft); border:1px solid var(--edge); border-radius:4px;
          padding:1px 5px; font-family:"Cascadia Mono",Consolas,monospace;
          font-size:13px; }}
  pre {{ background:#0B2545; color:#E8EEF5; padding:16px 20px; border-radius:9px;
         overflow:auto; font-size:13px; }}
  pre code {{ background:none; border:0; color:inherit; }}
  .kv td:first-child {{ width:34%; }}
  footer {{ text-align:center; color:var(--muted); font-size:13px; margin-top:34px; }}
  @media (max-width:720px) {{ .toc {{ columns:1; }} header.hero {{ padding:32px 22px; }} }}
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <h1>{title}</h1>
  <p>{subtitle}</p>
</header>
"""

    def to_html(self, subtitle: str = "", toc: list[tuple[str, str]] | None = None,
                toc_anchor: str = "contents") -> str:
        parts: list[str] = [self.HTML_HEAD.format(
            title=_html.escape(self.title),
            subtitle=_html.escape(subtitle),
        )]
        if toc:
            parts.append('<nav class="toc"><h2>Contents</h2>')
            for label, anchor in toc:
                parts.append(f'<a href="#{anchor}">{_html.escape(label)}</a>')
            parts.append("</nav>")
        for kind, payload in self.blocks:
            if kind == "h1":
                parts.append(f"<section id='sec-{_slug(payload)}'>")
                parts.append(f"<h1>{_html_inline(payload)}</h1>")
            elif kind == "h2":
                parts.append(f"<h2 id='{_slug(payload)}'>{_html_inline(payload)}</h2>")
            elif kind == "h3":
                parts.append(f"<h3>{_html_inline(payload)}</h3>")
            elif kind == "p":
                parts.append(f"<p>{_html_inline(payload)}</p>")
            elif kind == "note":
                parts.append(f"<blockquote>{_html_inline(payload)}</blockquote>")
            elif kind == "bullets":
                parts.append("<ul>")
                for it in payload:
                    parts.append(f"<li>{_html_inline(it)}</li>")
                parts.append("</ul>")
            elif kind == "code":
                parts.append(f"<pre><code>{_html.escape(payload)}</code></pre>")
            elif kind == "kv":
                parts.append('<table class="kv"><tbody>')
                for k, v in payload:
                    parts.append(f"<tr><td><strong>{_html_inline(k)}</strong></td>"
                                 f"<td>{_html_inline(v)}</td></tr>")
                parts.append("</tbody></table>")
            elif kind == "table":
                if payload["caption"]:
                    parts.append(f"<p><strong>{_html_inline(payload['caption'])}"
                                 "</strong></p>")
                parts.append("<table><thead><tr>")
                for c in payload["columns"]:
                    parts.append(f"<th>{_html_inline(c)}</th>")
                parts.append("</tr></thead><tbody>")
                for r in payload["rows"]:
                    parts.append("<tr>")
                    for c in r:
                        parts.append(f"<td>{_html_inline('' if c is None else c)}</td>")
                    parts.append("</tr>")
                parts.append("</tbody></table>")
            elif kind == "image":
                parts.append("<figure>")
                parts.append(f"<img src='{_html.escape(payload['path'])}' "
                             f"alt='{_html.escape(payload['caption'])}'>")
                if payload["caption"]:
                    parts.append(f"<figcaption>{_html_inline(payload['caption'])}"
                                 "</figcaption>")
                parts.append("</figure>")
            elif kind == "pagebreak":
                parts.append("</section><section>")
        parts.append("</section>")
        parts.append("<footer>Generated by data_analysis/build_report.py &mdash; "
                     "every number is reproducible from the datasets listed in the "
                     "appendix.</footer>")
        parts.append("</div></body></html>")
        return "\n".join(parts)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(text)).strip("-").lower()
    return s or "sec"


__all__ = ["Doc"]
