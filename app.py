import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
from datetime import date
import textwrap

# --------------------------------------------------
# Constants
# --------------------------------------------------
FOOTER_TEXT = "Confidential – Internal Use Only"
COVER_WIDTH = 1020
COVER_HEIGHT = 850

CATEGORIES = [
    "Outer Carton Packaging",
    "Box Labels",
    "Internal Packaging and Accessories",
    "Chassis View",
    "Composite Labels",
    "Internal Configuration",
    "CPU",
    "DIMM",
    "Drives",
    "Fan",
    "Adapter or IO Card",
    "PSU",
    "Internal Wiring"
]

# Max number of photos per category
MAX_PHOTOS = 5

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="NED FAI Report Generator",
    page_icon="hpe_logo.png",
    layout="centered"
)

# --------------------------------------------------
# Session state init
# --------------------------------------------------
if "draft" not in st.session_state:
    st.session_state.draft = []

if "preview_ready" not in st.session_state:
    st.session_state.preview_ready = False

# Initialize photo storage for each category
for cat in CATEGORIES:
    if cat not in st.session_state:
        st.session_state[cat] = [None] * MAX_PHOTOS

# --------------------------------------------------
# Sidebar
# --------------------------------------------------
st.sidebar.image("hpe_logo1.jfif", width=160)
st.sidebar.markdown("### NED FAI Report Generator")
st.sidebar.markdown("---")
st.sidebar.markdown("Internal HPE Tool")

# --------------------------------------------------
# Font loader
# --------------------------------------------------
def load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

# --------------------------------------------------
# Image optimization
# --------------------------------------------------
# def optimize_image(img, max_size=1920, quality=85):
#     img = ImageOps.exif_transpose(img)
#     w, h = img.size
#     long_edge = max(w, h)
#     if long_edge > max_size:
#         scale = max_size / long_edge
#         img = img.resize((int(w*scale), int(h*scale)), Image.Resampling.LANCZOS)
#     return img.convert("RGB"), quality

def optimize_image(img, max_size=3000, quality=95):
    """
    Preserve clarity for text-heavy photos.
    Minimal resizing, no forced orientation change.
    """
    img = ImageOps.exif_transpose(img)  # orientation-safe

    w, h = img.size
    long_edge = max(w, h)

    # Only resize if image is REALLY huge
    if long_edge > max_size:
        scale = max_size / long_edge
        img = img.resize(
            (int(w * scale), int(h * scale)),
            Image.Resampling.LANCZOS
        )

    return img.convert("RGB"), quality

# --------------------------------------------------
# Image render
# --------------------------------------------------
def render_image(img, label):
    img = img.copy()
    draw = ImageDraw.Draw(img)
    label_font = load_font(32)
    footer_font = load_font(20)

    padding = 20
    footer_gap = 10

    label_bbox = draw.textbbox((0, 0), label, font=label_font)
    label_h = label_bbox[3] - label_bbox[1]

    footer_bbox = draw.textbbox((0, 0), FOOTER_TEXT, font=footer_font)
    footer_h = footer_bbox[3] - footer_bbox[1]

    bar_h = label_h + footer_h + padding*2 + footer_gap

    canvas = Image.new("RGB", (img.width, img.height + bar_h), "white")
    canvas.paste(img, (0,0))

    d = ImageDraw.Draw(canvas)
    lw = d.textlength(label, font=label_font)
    d.text(((img.width-lw)//2, img.height + padding), label, fill="black", font=label_font)
    fw = d.textlength(FOOTER_TEXT, font=footer_font)
    d.text(((img.width-fw)//2, img.height+padding+label_h+footer_gap), FOOTER_TEXT, fill="gray", font=footer_font)

    return canvas

# --------------------------------------------------
# Main UI
# --------------------------------------------------
st.title("NED FAI Report Generator")
st.subheader("Report Information")

description = st.text_area("Description", height=120)

col1, col2 = st.columns(2)
with col1:
    kmatx_part_number = st.text_input("KMATX Part Number")
    sales_order = st.text_input("Sales Order")
with col2:
    halbX_part_number = st.text_input("HALBX Part Number")
    report_date = st.date_input("Date", value=date.today())

st.markdown("---")

# --------------------------------------------------
# Camera inputs per category
# --------------------------------------------------
st.subheader("📸 Take Photos by Category")

for cat in CATEGORIES:
    st.markdown(f"### {cat}")
    cols = st.columns(MAX_PHOTOS)
    for i in range(MAX_PHOTOS):
        key = f"{cat}_{i}"
        photo = cols[i].camera_input(f"Photo {i+1}", key=key)
        if photo:
            raw = Image.open(photo)
            img, _ = optimize_image(raw)
            st.session_state[cat][i] = img

    # Show uploaded photos for that category
    uploaded_imgs = [img for img in st.session_state[cat] if img]
    if uploaded_imgs:
        st.image(uploaded_imgs, caption=[f"{cat} #{i+1}" for i, img in enumerate(uploaded_imgs)], width=180)

    st.markdown("---")

# --------------------------------------------------
# Preview Final Draft
# --------------------------------------------------
if st.button("👀 Preview Final Draft"):
    draft = []
    for cat in CATEGORIES:
        for img in st.session_state[cat]:
            if img:
                draft.append({"include": True, "image": img, "label": cat})
    if not draft:
        st.error("Please take/upload at least one photo.")
        st.stop()
    st.session_state.draft = draft
    st.session_state.preview_ready = True

# --------------------------------------------------
# Draft editor
# --------------------------------------------------
if st.session_state.preview_ready:
    st.subheader("Final Draft Preview & Edit")
    for idx, item in enumerate(st.session_state.draft):
        colA, colB = st.columns([3, 2])
        with colA:
            item["include"] = st.checkbox("Include in PDF", value=item["include"], key=f"inc_{idx}")
            item["label"] = st.text_input("Label", value=item["label"], key=f"lbl_{idx}")
        with colB:
            st.image(render_image(item["image"], item["label"]), use_container_width=True)
        st.markdown("---")

# --------------------------------------------------
# Convert to PDF
# --------------------------------------------------
if st.button("📄 Convert to PDF"):
    selected = [i for i in st.session_state.draft if i["include"]]
    if not selected:
        st.error("No images selected for PDF.")
        st.stop()

    pdf_pages = []

    # COVER PAGE
    cover = Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT), "white")
    d = ImageDraw.Draw(cover)
    title_font = load_font(56)
    field_font = load_font(30)
    desc_font = load_font(26)
    footer_font = load_font(18)

    y = 90
    d.text((COVER_WIDTH//2, y), "NED FAI REPORT", font=title_font, fill="black", anchor="mm")
    y += 90
    d.text((60, y), "Description:", font=field_font, fill="black")
    y += 45
    for line in textwrap.wrap(description, 60):
        d.text((80, y), line, font=desc_font, fill="black")
        y += 34
    y += 30
    d.text((60, y), f"KMATX Part Number : {kmatx_part_number}", font=field_font, fill="black")
    y += 50
    d.text((60, y), f"HALBX Part Number : {halbX_part_number}", font=field_font, fill="black")
    y += 50
    d.text((60, y), f"Sales Order : {sales_order}", font=field_font, fill="black")
    y += 50
    d.text((60, y), f"Date : {report_date.strftime('%d %b %Y')}", font=field_font, fill="black")
    d.text((COVER_WIDTH//2, COVER_HEIGHT-35), FOOTER_TEXT, font=footer_font, fill="gray", anchor="mm")
    pdf_pages.append(cover)

    # IMAGE PAGES
    for item in selected:
        pdf_pages.append(render_image(item["image"], item["label"]))

    # SAVE PDF
    buffer = io.BytesIO()
    pdf_pages[0].save(buffer, format="PDF", save_all=True, append_images=pdf_pages[1:], resolution=300, optimize=True)
    buffer.seek(0)

    st.success("PDF created successfully!")
    st.download_button("⬇️ Download PDF", data=buffer, file_name="NED_FAI_Report.pdf", mime="application/pdf")

