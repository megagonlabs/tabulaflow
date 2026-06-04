# Debug fixture assets

Files in this directory are loaded by `_build_debug_media_result_widget`
when `DEBUG=1` is set. They are runtime-loaded via `importlib.resources`,
so they ship with the wheel.

## sample.mp4

`Big Buck Bunny`, Blender Foundation, 2008.
Licensed under Creative Commons Attribution 3.0 (CC-BY 3.0).
360p / 10s / ~1 MB excerpt sourced from
<https://test-videos.co.uk/bigbuckbunny/>.

Attribution: © 2008 Blender Foundation | <https://www.bigbuckbunny.org/>

## jpeg_0.jpg … jpeg_4.jpg

Real-photo samples at varied aspect ratios (landscape, portrait, square,
widescreen, tall) sourced from <https://picsum.photos/> with deterministic
seeds. Backed by Unsplash, photographer-attributed at picsum.photos.
Used by the `jpeg` column in the debug-media fixture to exercise the
table's handling of non-uniform image aspects.

## gif_0.gif … gif_4.gif

Five real animated GIFs of varied sizes (8 KB – 1.8 MB) and dimensions
(195×229 – 480×480) used by the `gif` column. Mix of GIPHY content
(`gif_0/2/3/4`) and Wikimedia (`gif_1`, "Newton's cradle"). Exercises
both the inline data-URI path (small) and the sibling-file spill path
(large) for the same media column.

## pdf_0.pdf … pdf_4.pdf

Five small public-domain PDFs used by the `pdf` column in the debug-media
fixture. Vary by page count (1–16) and size (3 KB–88 KB) to exercise the
PDF-anchor renderer:

- `pdf_0.pdf` — RFC 1149, "A Standard for the Transmission of IP Datagrams
  on Avian Carriers" (April Fools, 1990). IETF, public-domain.
- `pdf_1.pdf` — Generic test PDF from <https://www.orimi.com/pdf-test.pdf>.
- `pdf_2.pdf` — Adobe sample financial document
  (`c4611_sample_explain.pdf`), used widely as a test fixture.
- `pdf_3.pdf` — RFC 7159, "The JavaScript Object Notation (JSON) Data
  Interchange Format" (2014). IETF, public-domain.
- `pdf_4.pdf` — RFC 1925, "The Twelve Networking Truths" (April Fools,
  1996). IETF, public-domain.
