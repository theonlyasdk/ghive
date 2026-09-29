"""Markdown renderer widget for Tkinter using markdown-it-py with GitHub Light styling."""

import io
import queue
import platform
import re
import tkinter as tk
import threading
import urllib.error
import urllib.request
import webbrowser
from typing import Dict, List, Optional
from html.parser import HTMLParser

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

try:
    from markdown_it import MarkdownIt

    _HAS_MARKDOWN_IT = True
except ImportError:
    _HAS_MARKDOWN_IT = False


class MarkdownText(tk.Text):
    """Read-only or interactive text widget that renders GitHub Flavored Markdown."""

    def __init__(self, parent: tk.Widget, **kwargs):
        system = platform.system().lower()
        base_family = "Segoe UI" if system == "windows" else ("Helvetica Neue" if system == "darwin" else "DejaVu Sans")
        mono_family = "Consolas" if system == "windows" else ("Menlo" if system == "darwin" else "Courier New")

        self.base_family = base_family
        self.mono_family = mono_family
        self.link_counter = 0
        self._link_callbacks: Dict[str, str] = {}
        self._images: List[tk.PhotoImage] = []
        self._image_requests: Dict[str, List[str]] = {}
        self._image_results = queue.Queue()
        self._image_data_by_name: Dict[str, bytes] = {}
        self._image_counter = 0
        self._image_width = 600

        # Default GitHub light theme styling
        default_opts = {
            "wrap": tk.WORD,
            "font": (base_family, 10),
            "foreground": "#1f2328",
            "background": "#ffffff",
            "relief": tk.FLAT,
            "bd": 0,
            "highlightthickness": 0,
            "selectbackground": "#b3d7ff",
            "spacing1": 2,
            "spacing3": 3,
            "cursor": "arrow",
        }
        default_opts.update(kwargs)
        super().__init__(parent, **default_opts)

        self._init_tags()
        self.bind("<Configure>", self._on_configure)
        self.after(100, self._poll_image_results)

    def _poll_image_results(self) -> None:
        """Apply completed downloads on Tk's main thread."""
        if not self.winfo_exists():
            return
        while True:
            try:
                url, image_data = self._image_results.get_nowait()
            except queue.Empty:
                break
            self._display_image(url, image_data)
        try:
            self.after(100, self._poll_image_results)
        except tk.TclError:
            pass

    def _load_image(self, url: str) -> None:
        """Fetch an image off the UI thread and add it to the text widget."""
        if not url:
            return

        def fetch() -> None:
            image_data = None
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "ghive/1.0"})
                with urllib.request.urlopen(request, timeout=15) as response:
                    image_data = response.read(10 * 1024 * 1024 + 1)
                if len(image_data) > 10 * 1024 * 1024:
                    image_data = None
            except (OSError, ValueError, urllib.error.URLError):
                pass
            self._image_results.put((url, image_data))

        threading.Thread(target=fetch, daemon=True).start()

    def _display_image(self, url: str, image_data: Optional[bytes]) -> None:
        placeholders = self._image_requests.get(url, [])
        if not image_data:
            for placeholder in placeholders:
                self._replace_image_placeholder(placeholder, "[Broken image]")
            return
        if not self.winfo_exists():
            return

        max_width = max(100, self.winfo_width() - 40)
        photo = None
        try:
            if Image is not None:
                image = Image.open(io.BytesIO(image_data))
                image.thumbnail((max_width, 500))
                photo = ImageTk.PhotoImage(image, master=self)
        except (OSError, ValueError):
            # Some Pillow plugins reject formats that Tk can still display.
            pass

        if photo is None:
            try:
                photo = tk.PhotoImage(data=image_data, master=self)
                scale = max(1, (photo.width() + max_width - 1) // max_width)
                if scale > 1:
                    photo = photo.subsample(scale, scale)
            except (tk.TclError, OSError, ValueError):
                photo = None

        if photo is None:
            for placeholder in placeholders:
                self._replace_image_placeholder(placeholder, "[Broken image]")
            return

        for placeholder in placeholders:
            self._replace_image_placeholder(placeholder, "", photo, image_data)
        self._images.append(photo)

    def _replace_image_placeholder(self, placeholder: Optional[str], text: str, photo=None, image_data=None) -> None:
        if not placeholder or not self.winfo_exists():
            return
        ranges = self.tag_ranges(placeholder)
        if len(ranges) != 2:
            return
        self.config(state=tk.NORMAL)
        start = ranges[0]
        self.delete(start, ranges[1])
        if photo is not None:
            image_index = self._image_counter
            self._image_counter += 1
            image_name = f"comment_image_{image_index}"
            image_tag = f"comment_image_click_{image_index}"
            self.image_create(start, image=photo, align=tk.TOP, name=image_name)
            self.insert(f"{start}+1c", "\n")
            self.tag_add(image_tag, start, f"{start}+1c")
            if image_data:
                self._image_data_by_name[image_name] = image_data
                self.tag_bind(
                    image_tag,
                    "<Button-1>",
                    lambda event, data=image_data: self._open_image_viewer(data),
                )
                self.tag_bind(image_tag, "<Enter>", lambda event: self.config(cursor="hand2"))
                self.tag_bind(image_tag, "<Leave>", lambda event: self.config(cursor="arrow"))
        elif text:
            self.insert(start, text + "\n")
        self.config(state=tk.DISABLED)
        self.fit_height()

    def _open_image_viewer(self, image_data: bytes) -> str:
        """Show a borderless, click-to-dismiss image viewer scaled to the display."""
        if not self.winfo_exists():
            return "break"

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        max_width = max(100, int(screen_width * 0.92))
        max_height = max(100, int(screen_height * 0.90))
        viewer = tk.Toplevel(self.winfo_toplevel())
        viewer.overrideredirect(True)
        viewer.geometry(f"{screen_width}x{screen_height}+0+0")
        viewer.configure(background="#17191c", cursor="hand2")
        try:
            viewer.attributes("-topmost", True)
        except tk.TclError:
            pass

        try:
            if Image is not None:
                source = Image.open(io.BytesIO(image_data))
                source_width, source_height = source.size
                scale = min(2.0, max_width / source_width, max_height / source_height)
                display_size = (
                    max(1, round(source_width * scale)),
                    max(1, round(source_height * scale)),
                )
                if display_size != source.size:
                    source = source.resize(display_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(source, master=viewer)
            else:
                photo = tk.PhotoImage(data=image_data, master=viewer)
                source_width, source_height = photo.width(), photo.height()
                if source_width > max_width or source_height > max_height:
                    divisor = max(
                        (source_width + max_width - 1) // max_width,
                        (source_height + max_height - 1) // max_height,
                    )
                    photo = photo.subsample(divisor, divisor)
                elif source_width * 2 <= max_width and source_height * 2 <= max_height:
                    photo = photo.zoom(2, 2)
        except (tk.TclError, OSError, ValueError):
            viewer.destroy()
            return "break"

        image_label = tk.Label(viewer, image=photo, background="#17191c", borderwidth=0)
        image_label.image = photo
        image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        viewer.bind("<Button-1>", lambda event: viewer.destroy())
        image_label.bind("<Button-1>", lambda event: viewer.destroy())
        viewer.bind("<Escape>", lambda event: viewer.destroy())
        viewer.focus_force()
        try:
            viewer.grab_set()
        except tk.TclError:
            pass
        return "break"

    def _init_tags(self) -> None:
        """Initialize style tags for headings, code, quotes, and links."""
        bf = self.base_family
        mf = self.mono_family

        self.tag_configure("h1", font=(bf, 16, "bold"), spacing1=10, spacing3=4, foreground="#1f2328")
        self.tag_configure("h2", font=(bf, 14, "bold"), spacing1=8, spacing3=4, foreground="#1f2328")
        self.tag_configure("h3", font=(bf, 12, "bold"), spacing1=6, spacing3=3, foreground="#1f2328")
        self.tag_configure("h4", font=(bf, 10, "bold"), spacing1=4, spacing3=2, foreground="#1f2328")

        self.tag_configure("bold", font=(bf, 10, "bold"))
        self.tag_configure("italic", font=(bf, 10, "italic"))
        self.tag_configure("bold_italic", font=(bf, 10, "bold italic"))
        self.tag_configure("strike", overstrike=True)

        self.tag_configure("code_inline", font=(mf, 9), background="#eff1f3", foreground="#1f2328")
        self.tag_configure(
            "code_block",
            font=(mf, 9),
            background="#f6f8fa",
            foreground="#1f2328",
            spacing1=4,
            spacing3=4,
            lmargin1=16,
            lmargin2=16,
            rmargin=16,
        )

        self.tag_configure(
            "blockquote",
            font=(bf, 10, "italic"),
            foreground="#57606a",
            lmargin1=20,
            lmargin2=20,
        )

        self.tag_configure("list_bullet", lmargin1=16, lmargin2=28)
        self.tag_configure("list_ordered", lmargin1=16, lmargin2=28)
        self.tag_configure("hr", foreground="#d0d7de", justify=tk.CENTER)

    def set_markdown(self, markdown_content: str) -> None:
        """Parse and render markdown content into the text widget."""
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self._image_requests.clear()

        if not markdown_content or not markdown_content.strip():
            self.config(state=tk.DISABLED)
            return

        if not _HAS_MARKDOWN_IT:
            self._render_markdown_fallback(markdown_content)
            self.config(state=tk.DISABLED)
            return

        try:
            md = MarkdownIt("commonmark", {"html": True})
            tokens = md.parse(markdown_content)
            self._render_tokens(tokens)
        except Exception:
            # Fallback to raw text if parsing fails
            self.delete("1.0", tk.END)
            self.insert("1.0", markdown_content)

        # Remove trailing excessive newlines
        while True:
            end_val = self.get("end-2c", "end-1c")
            if end_val == "\n":
                self.delete("end-2c", "end-1c")
            else:
                break

        self.config(state=tk.DISABLED)

    def _render_markdown_fallback(self, markdown_content: str) -> None:
        """Keep comment text readable and load standard Markdown images without markdown-it."""
        image_pattern = re.compile(r"!\[([^\]]*)\]\(<?(https?://[^\s)>]+)>?(?:\s+['\"][^)]*['\"])?\)")
        position = 0
        for match in image_pattern.finditer(markdown_content):
            self.insert(tk.END, markdown_content[position:match.start()])
            self._insert_image_placeholder(match.group(2), match.group(1) or "image")
            position = match.end()
        self.insert(tk.END, markdown_content[position:])

    def _render_tokens(self, tokens: list) -> None:
        in_list = 0
        list_type: List[str] = []
        ordered_index: List[int] = []
        in_quote = False
        current_heading: Optional[str] = None

        for token in tokens:
            ttype = token.type

            if ttype in ("html_block",):
                self._insert_html_images(token.content)

            elif ttype == "heading_open":
                current_heading = token.tag.lower()
            elif ttype == "heading_close":
                self.insert(tk.END, "\n\n")
                current_heading = None

            elif ttype == "bullet_list_open":
                in_list += 1
                list_type.append("bullet")
            elif ttype == "bullet_list_close":
                in_list = max(0, in_list - 1)
                if list_type:
                    list_type.pop()
                self.insert(tk.END, "\n")

            elif ttype == "ordered_list_open":
                in_list += 1
                list_type.append("ordered")
                ordered_index.append(1)
            elif ttype == "ordered_list_close":
                in_list = max(0, in_list - 1)
                if list_type:
                    list_type.pop()
                if ordered_index:
                    ordered_index.pop()
                self.insert(tk.END, "\n")

            elif ttype == "list_item_open":
                indent = "    " * (in_list - 1)
                tag = "list_bullet"
                if list_type and list_type[-1] == "ordered" and ordered_index:
                    num = ordered_index[-1]
                    ordered_index[-1] += 1
                    prefix = f"{indent}{num}.  "
                    tag = "list_ordered"
                else:
                    prefix = f"{indent}•  "
                self.insert(tk.END, prefix, (tag,))

            elif ttype == "list_item_close":
                self.insert(tk.END, "\n")

            elif ttype == "blockquote_open":
                in_quote = True
            elif ttype == "blockquote_close":
                in_quote = False
                self.insert(tk.END, "\n")

            elif ttype in ("fence", "code_block"):
                code_text = token.content.rstrip("\n")
                self.insert(tk.END, f"{code_text}\n", ("code_block",))
                self.insert(tk.END, "\n")

            elif ttype == "hr":
                self.insert(tk.END, "────────────────────────────────────────\n\n", ("hr",))

            elif ttype == "inline":
                active_tags: List[str] = []
                if current_heading:
                    active_tags.append(current_heading)
                if in_quote:
                    active_tags.append("blockquote")

                for child in (token.children or []):
                    ctype = child.type
                    if ctype == "text":
                        raw = child.content
                        raw = raw.replace("[ ] ", "☐ ").replace("[x] ", "☑ ").replace("[X] ", "☑ ")
                        self.insert(tk.END, raw, tuple(active_tags))
                    elif ctype == "strong_open":
                        active_tags.append("bold")
                    elif ctype == "strong_close":
                        if "bold" in active_tags:
                            active_tags.remove("bold")
                    elif ctype == "em_open":
                        active_tags.append("italic")
                    elif ctype == "em_close":
                        if "italic" in active_tags:
                            active_tags.remove("italic")
                    elif ctype == "s_open":
                        active_tags.append("strike")
                    elif ctype == "s_close":
                        if "strike" in active_tags:
                            active_tags.remove("strike")
                    elif ctype == "code_inline":
                        self.insert(tk.END, f" {child.content} ", ("code_inline",))
                    elif ctype == "image":
                        url = child.attrs.get("src", "") if child.attrs else ""
                        alt = "".join(
                            nested.content for nested in (child.children or [])
                            if nested.type in ("text", "code_inline")
                        ) or child.content or "image"
                        if url.startswith(("https://", "http://")):
                            self._insert_image_placeholder(url, alt)
                        else:
                            self.insert(tk.END, f"[Image: {alt}]\n")
                    elif ctype == "html_inline":
                        self._insert_html_images(child.content)
                    elif ctype == "link_open":
                        url = child.attrs.get("href", "") if child.attrs else ""
                        self.link_counter += 1
                        ltag = f"link_{self.link_counter}"
                        self.tag_configure(ltag, foreground="#0969da", underline=True)
                        if url:
                            self.tag_bind(ltag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
                            self.tag_bind(ltag, "<Enter>", lambda e: self.config(cursor="hand2"))
                            self.tag_bind(ltag, "<Leave>", lambda e: self.config(cursor="arrow"))
                        active_tags.append(ltag)
                    elif ctype == "link_close":
                        active_tags = [t for t in active_tags if not t.startswith("link_")]
                    elif ctype in ("softbreak", "hardbreak"):
                        self.insert(tk.END, "\n", tuple(active_tags))

            elif ttype == "paragraph_close":
                if not in_list:
                    self.insert(tk.END, "\n\n")

    def _insert_image_placeholder(self, url: str, alt: str) -> None:
        placeholder = f"image_placeholder_{len(self._image_requests)}_{self.index(tk.END).replace('.', '_')}_{len(self._image_requests.get(url, []))}"
        self.insert(tk.END, f"[Loading image: {alt}]\n", (placeholder,))
        existing_placeholders = self._image_requests.setdefault(url, [])
        should_load = not existing_placeholders
        existing_placeholders.append(placeholder)
        if should_load:
            self._load_image(url)

    def _insert_html_images(self, html: str) -> None:
        class ImageParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.images = []
                self.text = []

            def handle_starttag(self, tag, attrs):
                if tag.lower() == "img":
                    values = dict(attrs)
                    self.images.append((values.get("src", ""), values.get("alt", "image")))

            def handle_data(self, data):
                if data.strip():
                    self.text.append(data.strip())

            handle_startendtag = handle_starttag

        parser = ImageParser()
        try:
            parser.feed(html)
        except (ValueError, AssertionError):
            return
        if parser.text:
            self.insert(tk.END, " ".join(parser.text) + "\n")
        for url, alt in parser.images:
            if url.startswith(("https://", "http://")):
                self._insert_image_placeholder(url, alt)

    def _on_configure(self, event=None) -> None:
        """Handle configure/resize events to re-fit display lines."""
        if self.winfo_width() > 50:
            self.fit_height()

    def fit_height(self, min_lines: int = 1, max_lines: int = 500) -> None:
        """Auto-adjust height based on visual display lines so content is never scrolled internally."""
        if getattr(self, "_fitting", False):
            return
        self._fitting = True
        try:
            if self.winfo_width() > 50:
                res = self.count("1.0", "end-1c", "displaylines")
                if res and res[0] is not None:
                    line_count = int(res[0])
                else:
                    line_count = int(self.index("end-1c").split(".")[0])
            else:
                line_count = int(self.index("end-1c").split(".")[0])
            target_height = max(min_lines, min(max_lines, line_count))

            try:
                curr = int(self.cget("height"))
            except Exception:
                curr = -1
            if curr != target_height:
                self.config(height=target_height)

            # Iteratively expand if font size, headings or block margins overflow widget height
            if self.winfo_exists() and self.winfo_width() > 50:
                self.update_idletasks()
                attempts = 0
                while attempts < 40 and target_height < max_lines:
                    yv = self.yview()
                    if yv[1] >= 1.0 or (yv[1] - yv[0]) >= 0.999:
                        break
                    visible_ratio = yv[1] - yv[0]
                    if visible_ratio > 0.05:
                        needed = max(target_height + 1, int(round(target_height / visible_ratio)))
                    else:
                        needed = target_height + 2
                    target_height = min(max_lines, needed)
                    self.config(height=target_height)
                    self.update_idletasks()
                    attempts += 1
        except Exception:
            pass
        finally:
            self._fitting = False
